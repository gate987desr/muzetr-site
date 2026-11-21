/* ==========================================================================
   饮冰室 · unlock.js
   Client-side decryption for password protected essays.

   Mirrors build.py: PBKDF2-SHA256 (salt, iterations) -> 32 byte key, then an
   HMAC-SHA256 counter keystream XORed with the ciphertext, verified by a
   16 byte HMAC tag. Nothing leaves the browser.
   ========================================================================== */

(function () {
  "use strict";

  var holder = document.getElementById("lock-data");
  var lock = document.querySelector("[data-lock]");
  if (!holder || !lock) return;

  var payload;
  try { payload = JSON.parse(holder.textContent); } catch (error) { return; }

  var form = document.querySelector("[data-lock-form]");
  var input = document.getElementById("lock-input");
  var status = document.querySelector("[data-lock-status]");
  var body = document.querySelector("[data-lock-body]");
  var slug = lock.getAttribute("data-slug") || "post";
  var storageKey = "icing.lock." + slug;

  function toBytes(base64) {
    var binary = window.atob(base64);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  function concat(first, second) {
    var out = new Uint8Array(first.length + second.length);
    out.set(first, 0);
    out.set(second, first.length);
    return out;
  }

  function counterBytes(value) {
    var bytes = new Uint8Array(4);
    new DataView(bytes.buffer).setUint32(0, value, false);
    return bytes;
  }

  function hmac(keyBytes, data) {
    return crypto.subtle.importKey("raw", keyBytes, { name: "HMAC", hash: "SHA-256" }, false, ["sign"])
      .then(function (key) { return crypto.subtle.sign("HMAC", key, data); })
      .then(function (buffer) { return new Uint8Array(buffer); });
  }

  function deriveKey(password, salt, iterations) {
    var encoder = new TextEncoder();
    return crypto.subtle.importKey("raw", encoder.encode(password), "PBKDF2", false, ["deriveBits"])
      .then(function (baseKey) {
        return crypto.subtle.deriveBits(
          { name: "PBKDF2", salt: salt, iterations: iterations, hash: "SHA-256" },
          baseKey,
          256
        );
      })
      .then(function (bits) { return new Uint8Array(bits); });
  }

  function decrypt(password) {
    var salt = toBytes(payload.salt);
    var nonce = toBytes(payload.nonce);
    var cipher = toBytes(payload.ct);
    var tag = toBytes(payload.tag);
    var key;

    return deriveKey(password, salt, payload.iter)
      .then(function (derived) {
        key = derived;
        var stream = [];
        var index = 0;
        var produce = function () {
          if (index * 32 >= cipher.length) return Promise.resolve();
          return hmac(key, concat(nonce, counterBytes(index))).then(function (bytes) {
            stream.push(bytes);
            index += 1;
            return produce();
          });
        };
        return produce().then(function () {
          var joined = new Uint8Array(stream.length * 32);
          stream.forEach(function (bytes, position) { joined.set(bytes, position * 32); });
          return joined;
        });
      })
      .then(function (keystream) {
        var plain = new Uint8Array(cipher.length);
        for (var i = 0; i < cipher.length; i += 1) plain[i] = cipher[i] ^ keystream[i];
        return hmac(key, concat(nonce, cipher)).then(function (digest) {
          var expected = digest.slice(0, 16);
          var same = expected.length === tag.length;
          if (same) {
            for (var j = 0; j < 16; j += 1) {
              if (expected[j] !== tag[j]) { same = false; break; }
            }
          }
          if (!same) throw new Error("wrong-password");
          return new TextDecoder().decode(plain);
        });
      });
  }

  function reveal(html) {
    if (!body) return;
    body.innerHTML = html;
    body.hidden = false;
    lock.classList.add("is-open");
    if (status) status.textContent = "";
  }

  function attempt(password, remember) {
    if (status) status.textContent = "正在开封…";
    return decrypt(password).then(function (html) {
      reveal(html);
      lock.setAttribute("data-unlocked", "1");
      if (remember) {
        try { sessionStorage.setItem(storageKey, password); } catch (error) {}
      }
      return true;
    }).catch(function () {
      if (status) status.textContent = "口令不对。再想想？";
      return false;
    });
  }

  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var password = (input.value || "").trim();
      if (!password) return;
      attempt(password, true);
    });
  }

  var remembered = null;
  try { remembered = sessionStorage.getItem(storageKey); } catch (error) {}
  if (remembered) attempt(remembered, false);
})();
