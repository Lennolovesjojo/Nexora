/* Nexora Website – Interaktionen
   Einstellungen (Calendly-Link, E-Mail-Adressen, WhatsApp) stehen in _build/build.py
   und kommen über data-Attribute im HTML hier an. */

(() => {
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fine = matchMedia("(hover: hover) and (pointer: fine)").matches;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

  /* ---------- Seitenübergang ---------- */
  const curtain = $(".curtain");
  const enter = () => requestAnimationFrame(() => requestAnimationFrame(() => root.classList.remove("entering", "leaving")));
  enter();
  addEventListener("pageshow", e => { if (e.persisted) enter(); });

  document.addEventListener("click", e => {
    const a = e.target.closest("a[href]");
    if (!a || !curtain || reduce) return;
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (a.target === "_blank" || a.hasAttribute("download")) return;
    const href = a.getAttribute("href");
    if (!href || href.startsWith("#") || /^(mailto:|tel:|https?:|\/\/)/i.test(href)) return;
    const url = new URL(a.href);
    if (url.origin !== location.origin || url.pathname === location.pathname) return; // fremde Seite oder Anker auf derselben Seite
    e.preventDefault();
    curtain.style.transition = "none";
    curtain.style.transform = "translateY(100%)";
    curtain.offsetHeight; // reflow
    curtain.style.transition = "";
    curtain.style.transform = "";
    root.classList.add("leaving");
    setTimeout(() => { location.href = url.href; }, 620);
  });

  /* ---------- Header, Fortschritt ---------- */
  const head = $(".site-head");
  const bar = $(".progress");
  const onScroll = () => {
    const y = scrollY;
    head && head.classList.toggle("scrolled", y > 8);
    if (bar) {
      const max = document.documentElement.scrollHeight - innerHeight;
      bar.style.transform = `scaleX(${max > 0 ? y / max : 0})`;
    }
  };

  /* ---------- Mobile Menü ---------- */
  const menuBtn = $("#menuBtn");
  if (menuBtn) {
    const setMenu = open => {
      head.classList.toggle("open", open);
      menuBtn.setAttribute("aria-expanded", String(open));
      menuBtn.setAttribute("aria-label", open ? "Menü schließen" : "Menü öffnen");
    };
    const isOpen = () => head.classList.contains("open");
    menuBtn.addEventListener("click", () => setMenu(!isOpen()));
    $$(".mobile-nav a").forEach(a => a.addEventListener("click", () => setMenu(false)));
    document.addEventListener("keydown", e => {
      if (e.key === "Escape" && isOpen()) { setMenu(false); menuBtn.focus(); }
    });
    document.addEventListener("click", e => { if (isOpen() && !head.contains(e.target)) setMenu(false); });
  }

  /* ---------- Überschriften Wort für Wort ---------- */
  const splitText = el => {
    const walk = node => {
      [...node.childNodes].forEach(n => {
        if (n.nodeType === 3) {
          const frag = document.createDocumentFragment();
          n.textContent.split(/(\s+)/).forEach(part => {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); return; }
            const w = document.createElement("span"), inner = document.createElement("span");
            w.className = "w"; inner.textContent = part; w.appendChild(inner); frag.appendChild(w);
          });
          n.replaceWith(frag);
        } else if (n.nodeType === 1 && n.tagName !== "BR") {
          if (n.classList.contains("grad-text")) {
            const w = document.createElement("span"); w.className = "w";
            n.replaceWith(w); w.appendChild(n);
          } else walk(n);
        }
      });
    };
    walk(el);
    $$(".w > *", el).forEach((s, i) => s.style.setProperty("--wi", i));
    el.classList.remove("reveal");
    el.classList.add("split");
    el.setAttribute("data-obs", "");
  };
  if (!reduce) $$("h2.reveal, .page-hero h1.reveal").forEach(splitText);

  /* ---------- Einblenden beim Scrollen ---------- */
  const show = el => {
    el.classList.add("in");
    if (el.classList.contains("reveal")) setTimeout(() => el.classList.remove("reveal"), 1500);
  };
  const targets = $$(".reveal, [data-obs]");
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver(entries => entries.forEach(e => {
      if (e.isIntersecting) { show(e.target); io.unobserve(e.target); }
    }), { rootMargin: "0px 0px -10% 0px", threshold: .08 });
    targets.forEach(el => io.observe(el));
  } else targets.forEach(show);

  /* ---------- Zähler ---------- */
  const fmt = (n, d) => n.toLocaleString("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d });
  const counters = $$("[data-count]");
  const runCount = el => {
    const to = parseFloat(el.dataset.count), d = +(el.dataset.decimals || 0);
    if (reduce) { el.textContent = fmt(to, d); return; }
    const from = parseFloat(el.dataset.from || 0), dur = 2000, t0 = performance.now();
    const tick = t => {
      const p = clamp((t - t0) / dur, 0, 1), e = 1 - Math.pow(1 - p, 4);
      el.textContent = fmt(from + (to - from) * e, d);
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  if ("IntersectionObserver" in window) {
    const cio = new IntersectionObserver(entries => entries.forEach(e => {
      if (e.isIntersecting) { runCount(e.target); cio.unobserve(e.target); }
    }), { threshold: .6 });
    counters.forEach(el => cio.observe(el));
  }

  /* ---------- Hero: Wortwechsel ---------- */
  const rot = $(".rotator");
  if (rot && !reduce) {
    const words = $$("span", rot);
    let i = 0;
    setInterval(() => {
      const cur = words[i], next = words[(i + 1) % words.length];
      cur.classList.remove("on"); cur.classList.add("out");
      next.classList.remove("out"); next.classList.add("on");
      setTimeout(() => cur.classList.remove("out"), 800);
      i = (i + 1) % words.length;
    }, 2600);
  }

  /* ---------- Hero: Farbverlauf-Canvas ---------- */
  const canvas = $(".hero canvas");
  let mx = 0, my = 0, tmx = 0, tmy = 0;
  if (canvas) {
    const ctx = canvas.getContext("2d");
    const blobs = [
      { x: .18, y: .22, r: .42, c: "106,27,214", a: .20, s: .00021, p: 0 },
      { x: .84, y: .18, r: .40, c: "22,103,240", a: .17, s: .00017, p: 2.1 },
      { x: .55, y: .62, r: .48, c: "169,156,235", a: .26, s: .00013, p: 4.2 },
      { x: .30, y: .80, r: .30, c: "75,59,234", a: .10, s: .00025, p: 1.3 }
    ];
    let W = 0, H = 0, running = !reduce, raf = 0;
    const size = () => {
      const r = canvas.getBoundingClientRect();
      W = canvas.width = Math.max(1, Math.round(r.width * .5));
      H = canvas.height = Math.max(1, Math.round(r.height * .5));
    };
    const draw = t => {
      mx += (tmx - mx) * .04; my += (tmy - my) * .04;
      ctx.clearRect(0, 0, W, H);
      const M = Math.max(W, H);
      for (const b of blobs) {
        const x = (b.x + Math.sin(t * b.s + b.p) * .07 + mx * .04) * W;
        const y = (b.y + Math.cos(t * b.s * 1.3 + b.p) * .06 + my * .04) * H;
        const g = ctx.createRadialGradient(x, y, 0, x, y, b.r * M);
        g.addColorStop(0, `rgba(${b.c},${b.a})`);
        g.addColorStop(1, `rgba(${b.c},0)`);
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, W, H);
      }
    };
    const loop = t => { draw(t); if (running) raf = requestAnimationFrame(loop); };
    size(); draw(0);
    addEventListener("resize", () => { size(); draw(performance.now()); });
    if (!reduce) {
      const hio = new IntersectionObserver(([e]) => {
        running = e.isIntersecting;
        cancelAnimationFrame(raf);
        if (running) raf = requestAnimationFrame(loop);
      });
      hio.observe(canvas);
    }
  }

  /* ---------- Hero: Bühne, Parallaxe ---------- */
  const hero = $(".hero");
  const screen = $(".screen");
  const floats = $$(".float");
  if (hero && fine && !reduce) {
    hero.addEventListener("pointermove", e => {
      const r = hero.getBoundingClientRect();
      tmx = (e.clientX - r.left) / r.width * 2 - 1;
      tmy = (e.clientY - r.top) / r.height * 2 - 1;
      floats.forEach(f => {
        const d = +(f.dataset.depth || 10);
        f.style.translate = `${(tmx * d).toFixed(1)}px ${(tmy * d).toFixed(1)}px`;
      });
    });
    hero.addEventListener("pointerleave", () => { tmx = tmy = 0; floats.forEach(f => f.style.translate = ""); });
  }
  const flatten = () => {
    if (!screen || reduce) return;
    const r = screen.getBoundingClientRect();
    const p = clamp(1 - (r.top - innerHeight * .25) / (innerHeight * .55), 0, 1);
    screen.style.transform = `rotateX(${(10 * (1 - p)).toFixed(2)}deg) scale(${(.96 + .04 * p).toFixed(3)})`;
  };

  /* ---------- Ablauf: Linie füllt sich ---------- */
  const tl = $(".timeline");
  const fill = $(".timeline .fill");
  const timeline = () => {
    if (!tl || !fill) return;
    const r = tl.getBoundingClientRect();
    const p = clamp((innerHeight * .6 - r.top) / r.height, 0, 1);
    fill.style.setProperty("--p", p.toFixed(3));
  };

  let ticking = false;
  const frame = () => { onScroll(); flatten(); timeline(); ticking = false; };
  addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(frame); } }, { passive: true });
  addEventListener("resize", frame);
  frame();

  /* ---------- Spotlight auf Karten ---------- */
  if (fine) {
    $$(".card, .job-card, .plan").forEach(el => {
      el.addEventListener("pointermove", e => {
        const r = el.getBoundingClientRect();
        el.style.setProperty("--mx", `${e.clientX - r.left}px`);
        el.style.setProperty("--my", `${e.clientY - r.top}px`);
      });
    });
  }

  /* ---------- Design-Karte: Beispiel-Designs wechseln, der Cursor wählt die Farbe ---------- */
  const studio = $(".studio");
  if (studio) {
    const cur = $(".sb-cursor", studio), dots = $$(".sb-sw i", studio), desk = $(".sb-desk", studio);
    let theme = 0, timer = 0, live = false, hold = 0;
    // Pfeilspitze (3|2,5 im Symbol) auf einen Punkt des Zielelements setzen
    const at = (el, fx, fy, dx, dy) => {
      if (!el) return;
      const c = studio.getBoundingClientRect(), r = el.getBoundingClientRect();
      cur.style.transform = `translate(${Math.round(r.left - c.left + r.width * fx + dx - 3)}px,${Math.round(r.top - c.top + r.height * fy + dy - 2.5)}px)`;
    };
    // Ruheposition: Anfasser unten rechts am Auswahlrahmen der sichtbaren Überschrift
    const rest = () => {
      const h = $((desk && desk.offsetParent ? ".sb-desk" : ".sb-phone") + " .sb-h", studio);
      at(h && h.children[+studio.dataset.theme || 0], 1, 1, 5.75, 5.75);
    };
    const pick = i => { theme = i; studio.dataset.theme = i; };
    const step = () => {
      if (Date.now() < hold) { timer = setTimeout(step, 1000); return; }
      const next = (theme + 1) % dots.length;
      at(dots[next], .5, .5, 0, 0);
      timer = setTimeout(() => {
        cur.classList.add("is-click");
        pick(next);
        setTimeout(() => cur.classList.remove("is-click"), 240);
        timer = setTimeout(() => { rest(); timer = setTimeout(step, 2600); }, 700);
      }, 1050);
    };
    const run = () => { clearTimeout(timer); timer = live && !document.hidden ? setTimeout(step, 1500) : 0; };
    // Cursor erst setzen, wenn die Karte in Sicht kommt (spart Arbeit beim Laden der Seite)
    let placed = false;
    const place = () => { if (placed) rest(); };
    const first = () => { placed = true; rest(); requestAnimationFrame(() => studio.classList.add("sb-on")); };
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(([e]) => {
        if (e.isIntersecting && !placed) first();
        live = e.intersectionRatio >= .4;
        if (!reduce) run();
      }, { threshold: [0, .4] }).observe(studio);
      if (!reduce) document.addEventListener("visibilitychange", run);
    } else first();
    addEventListener("resize", place);
    addEventListener("load", place);
    if (document.fonts) document.fonts.ready.then(place);
    dots.forEach((d, i) => d.addEventListener("click", () => { pick(i); hold = Date.now() + 6000; }));
  }

  /* ---------- Footer: Lichtkegel über dem Schriftzug ---------- */
  const big = $(".foot-big");
  if (big && fine && !reduce) {
    const foot = big.closest(".site-foot");
    foot.addEventListener("pointermove", e => {
      const r = big.getBoundingClientRect();
      big.style.setProperty("--fx", `${e.clientX - r.left}px`);
      big.style.setProperty("--fy", `${e.clientY - r.top}px`);
    });
    foot.addEventListener("pointerleave", () => big.style.setProperty("--fx", "-400px"));
  }

  /* ---------- Magnetische Buttons ---------- */
  if (fine && !reduce) {
    $$(".magnetic").forEach(b => {
      b.addEventListener("pointermove", e => {
        const r = b.getBoundingClientRect();
        const x = (e.clientX - r.left - r.width / 2) * .22;
        const y = (e.clientY - r.top - r.height / 2) * .35;
        b.style.translate = `${x.toFixed(1)}px ${y.toFixed(1)}px`;
      });
      b.addEventListener("pointerleave", () => { b.style.translate = ""; });
    });
  }

  /* ---------- Uptime-Balken ---------- */
  $$(".uptime").forEach(u => {
    for (let i = 0; i < 30; i++) {
      const s = document.createElement("i");
      s.style.transitionDelay = `${i * 25}ms`;
      if (i === 17) s.style.height = "82%";
      u.appendChild(s);
    }
  });

  /* ---------- E-Mail kopieren ---------- */
  $$("[data-copy]").forEach(btn => btn.addEventListener("click", () => {
    const text = btn.dataset.copy, label = btn.textContent;
    const done = () => { btn.textContent = "Kopiert"; setTimeout(() => btn.textContent = label, 1600); };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, () => selectCode(btn));
    else selectCode(btn);
  }));
  function selectCode(btn) {
    const code = btn.parentElement.querySelector("code");
    if (!code) return;
    const r = document.createRange(); r.selectNodeContents(code);
    const s = getSelection(); s.removeAllRanges(); s.addRange(r);
  }

  /* ---------- Jahr ---------- */
  $$("[data-year]").forEach(el => el.textContent = new Date().getFullYear());

  /* ---------- Formulare: Bewerbung und Anfrage ---------- */
  const initForm = (form, cfg) => {
    const F = n => form.elements.namedItem(n);
    const T = cfg.text;
    const mail = form.dataset.mail;
    const msg = $(".af-msg", form);
    const btn = $(".af-submit", form);
    const label = $(".af-label", form);
    const labelText = label.textContent;
    const file = F("lebenslauf");
    const link = F(cfg.link);
    const note = F("nachricht");
    const q = new URLSearchParams(location.search);
    const t0 = Date.now();

    // Auswahl aus dem Link übernehmen (z. B. bewerbung.html?stelle=developer, kontakt.html?anliegen=betreuung)
    const pre = q.get(cfg.choice);
    $$(`input[name="${cfg.choice}"]`, form).forEach(r => { if (r.value === pre) r.checked = true; });

    const fieldOf = el => el.closest(".af-field, .af-check");
    const setErr = (el, text) => {
      const box = fieldOf(el);
      box.classList.add("err");
      let e = $(".af-err", box);
      if (!e) {
        e = document.createElement("span");
        e.className = "af-err";
        e.id = `err-${el.name}`;
        box.appendChild(e);
      }
      e.textContent = text;
      el.setAttribute("aria-invalid", "true");
      el.setAttribute("aria-describedby", e.id);
    };
    const clearErr = el => {
      const box = el.name && fieldOf(el);
      if (!box || !box.classList.contains("err")) return;
      box.classList.remove("err");
      const e = $(".af-err", box);
      if (e) e.remove();
      $$("[aria-invalid]", box).forEach(x => { x.removeAttribute("aria-invalid"); x.removeAttribute("aria-describedby"); });
    };
    form.addEventListener("input", e => clearErr(e.target));
    form.addEventListener("change", e => clearErr(e.target));

    // Datei (nur Bewerbung): Name und Größe anzeigen, Ziehen und Ablegen hervorheben
    const MAX_MB = +form.dataset.maxMb || 10, MAX = MAX_MB * 1048576, TYPES = /\.(pdf|docx?|jpe?g|png)$/i;
    if (file) {
      const drop = $(".drop", form);
      const dropName = $(".drop-name", form);
      file.addEventListener("change", () => {
        const f = file.files[0];
        drop.classList.toggle("has", !!f);
        dropName.textContent = f ? `${f.name} · ${(f.size / 1048576).toFixed(f.size < 1048576 ? 2 : 1).replace(".", ",")} MB` : "";
      });
      ["dragenter", "dragover"].forEach(t => drop.addEventListener(t, () => drop.classList.add("over")));
      ["dragleave", "drop"].forEach(t => drop.addEventListener(t, () => drop.classList.remove("over")));
    }

    // Link ohne https:// ergänzen
    if (link) link.addEventListener("blur", () => {
      const v = link.value.trim();
      if (v && !/^https?:\/\//i.test(v)) link.value = `https://${v}`;
    });

    // Prüfung in der Reihenfolge der Felder, damit der Fokus beim ersten Fehler landet
    const validate = () => {
      let first = null;
      const bad = (el, text) => { setErr(el, text); first = first || el; };
      if (!$(`input[name="${cfg.choice}"]:checked`, form)) bad($(`input[name="${cfg.choice}"]`, form), T.choice);
      if (!F("name").value.trim()) bad(F("name"), T.name);
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(F("email").value.trim())) bad(F("email"), T.email);
      const f = file && file.files[0];
      if (f && f.size > MAX) bad(file, `Die Datei ist größer als ${MAX_MB} MB.`);
      else if (f && !TYPES.test(f.name)) bad(file, "Bitte lade eine PDF-, Word- oder Bilddatei hoch.");
      const lv = link ? link.value.trim() : "";
      if (lv && !/^https?:\/\/\S+\.\S+$/i.test(lv)) bad(link, T.link);
      if (cfg.needText && !note.value.trim()) bad(note, T.text);
      if (!F("datenschutz").checked) bad(F("datenschutz"), T.privacy);
      if (first) first.focus();
      return !first;
    };

    const fallback = text => {
      msg.replaceChildren(text || "Das Senden hat leider nicht geklappt. ");
      if (!text) {
        const a = document.createElement("a");
        a.href = `mailto:${mail}`;
        a.textContent = mail;
        msg.append(T.direct, a, ".");
      }
    };
    const done = () => {
      form.classList.add("is-done");
      const d = $(".af-done", form);
      d.hidden = false;
      d.tabIndex = -1;
      d.focus({ preventScroll: true });
      const top = form.getBoundingClientRect().top + scrollY - 110;
      if (top < scrollY) scrollTo({ top, behavior: reduce ? "auto" : "smooth" });
    };

    // Rückkehr ohne JavaScript-Versand (Weiterleitung vom Server)
    if (q.get("status") === "gesendet") done();
    if (q.get("status") === "fehler") fallback();

    form.addEventListener("submit", async e => {
      e.preventDefault();
      msg.replaceChildren();
      if (!validate()) return;
      const data = new FormData(form);
      data.set("dauer", String(Math.round((Date.now() - t0) / 1000)));
      btn.disabled = true;
      form.classList.add("is-sending");
      label.textContent = "Wird gesendet …";
      try {
        const res = await fetch(form.action, { method: "POST", body: data, headers: { Accept: "application/json" } });
        let out = {};
        try { out = await res.json(); } catch (_) { /* keine JSON-Antwort, z. B. Server ohne PHP */ }
        if (res.ok && out.ok) { done(); return; }
        fallback(res.status < 500 && out.error ? out.error : "");
      } catch (_) {
        fallback("");
      } finally {
        btn.disabled = false;
        form.classList.remove("is-sending");
        label.textContent = labelText;
      }
    });
  };

  const applyForm = $("#applyForm");
  if (applyForm) initForm(applyForm, {
    choice: "stelle", link: "link", needText: false,
    text: {
      choice: "Bitte wähle eine Stelle aus.",
      name: "Bitte gib deinen Namen ein.",
      email: "Bitte gib eine gültige E-Mail-Adresse ein.",
      link: "Bitte gib einen vollständigen Link ein, zum Beispiel https://linkedin.com/in/…",
      privacy: "Bitte bestätige die Datenschutzhinweise.",
      direct: "Schick deine Bewerbung gern direkt an ",
    },
  });
  const contactForm = $("#contactForm");
  if (contactForm) initForm(contactForm, {
    choice: "anliegen", link: "website", needText: true,
    text: {
      choice: "Bitte wählen Sie aus, worum es geht.",
      name: "Bitte geben Sie Ihren Namen ein.",
      email: "Bitte geben Sie eine gültige E-Mail-Adresse ein.",
      link: "Bitte geben Sie die vollständige Adresse ein, zum Beispiel https://ihre-firma.de",
      text: "Bitte schreiben Sie uns kurz, worum es geht.",
      privacy: "Bitte bestätigen Sie die Datenschutzhinweise.",
      direct: "Schreiben Sie uns gern direkt an ",
    },
  });

  /* ---------- Terminbuchung (Calendly) ---------- */
  const cal = $("#cal");
  if (cal && cal.dataset.url) {
    const u = new URL(cal.dataset.url);
    const q = u.searchParams;
    q.set("embed_domain", location.hostname || "nexora.de");
    q.set("embed_type", "Inline");
    q.set("hide_event_type_details", "1");   // Details stehen schon links auf der Seite
    q.set("hide_gdpr_banner", "1");
    q.set("primary_color", "6a1bd6");
    q.set("text_color", "0f0c22");
    q.set("background_color", "ffffff");

    const fallback = [...cal.childNodes];       // Karte mit direktem Link, falls der Kalender nicht laden darf
    const ask = $(".cal-ask", cal), direct = $(".cal-direct", cal);
    let started = false;

    const embed = () => {
      if (started) return;
      started = true;
      const loader = document.createElement("div");
      loader.className = "cal-loader";
      loader.innerHTML = '<img src="assets/logo-mark-144.png" alt="" width="46" height="46"><span>Kalender wird geladen …</span>';
      const frame = document.createElement("iframe");
      frame.title = "Beratungstermin bei Nexora buchen";
      frame.src = u.href;
      let alive = false;
      const ready = () => { if (frame.isConnected) { alive = true; cal.classList.add("ready"); } };
      const showFallback = () => {
        cal.classList.remove("embed", "ready");
        if (ask) ask.hidden = true;
        if (direct) direct.hidden = false;
        cal.replaceChildren(...fallback);
      };
      frame.addEventListener("load", ready);
      cal.classList.add("embed");
      cal.replaceChildren(loader, frame);

      addEventListener("message", e => {
        if (!/^https:\/\/([\w-]+\.)*calendly\.com$/.test(e.origin)) return;
        const d = e.data || {};
        if (typeof d.event !== "string" || !d.event.startsWith("calendly.")) return;
        ready();
        if (d.event === "calendly.page_height" && d.payload) {
          const h = parseInt(d.payload.height, 10);
          if (h > 320) frame.style.height = `${h}px`;   // Höhe folgt dem Inhalt, keine doppelte Scrollleiste
        }
      });
      document.addEventListener("securitypolicyviolation", e => {
        if (String(e.blockedURI).includes("calendly")) showFallback();
      });
      setTimeout(() => { if (!alive && frame.isConnected) showFallback(); }, 20000);
    };

    if (cal.dataset.consent === "1" && ask && direct) {
      // Datenschutz: Calendly lädt erst nach einem Klick auf "Kalender anzeigen"
      ask.hidden = false;
      direct.hidden = true;
      $(".cal-load", ask).addEventListener("click", () => {
        embed();
        cal.tabIndex = -1;
        cal.focus({ preventScroll: true });   // Tastatur: weiter geht es im Kalender
      });
    } else embed();
  }
})();
