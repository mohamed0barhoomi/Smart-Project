/* ==========================================================
   SmartProjects - lamp_login.js
   Lampe interactive de la page de connexion (JavaScript pur, sans bibliothèque).
   - on tire le cordon (glisser vers le bas) pour allumer / éteindre
   - le formulaire apparaît quand la lampe est allumée
   - 5 couleurs de lumière, poussière lumineuse, petit son (optionnel)
   ========================================================== */
(function () {
    "use strict";

    const body = document.body;
    const svg = document.querySelector(".lamp-svg");
    const bead = document.getElementById("cordBead");
    const cord = document.getElementById("elasticCord");
    const userField = document.getElementById("id_username");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // ---------- Allumer / éteindre ----------
    let soundOn = localStorage.getItem("lampSound") !== "off";

    function setLamp(on) {
        body.dataset.on = on ? "true" : "false";
        bead.setAttribute("aria-pressed", on ? "true" : "false");
        if (on) {
            startDust();
            // on met le curseur dans le premier champ une fois la carte affichée
            setTimeout(function () { if (userField && !userField.value) userField.focus(); }, 650);
        } else {
            stopDust();
        }
    }

    function toggleLamp() {
        const on = body.dataset.on !== "true";
        click(on);
        setLamp(on);
    }

    // ---------- Cordon : glisser-déposer ----------
    const REST = { x: 245, y: 300 };   // position de repos de la perle (coordonnées du SVG)
    const MAX_PULL = 70;               // tirage maximum vers le bas
    const TRIGGER = 38;                // à partir de là, l'interrupteur se déclenche
    let pos = { x: REST.x, y: REST.y };
    let dragging = false, triggered = false, moved = false, startPointer = null, springFrame = null;

    function draw() {
        bead.setAttribute("transform", "translate(" + pos.x + " " + pos.y + ")");
        const midY = 212 + (pos.y - 212) / 2;
        cord.setAttribute("d", "M 245 212 Q 245 " + midY + " " + pos.x + " " + (pos.y - 8));
    }

    function toSvgPoint(event) {
        const point = svg.createSVGPoint();
        point.x = event.clientX;
        point.y = event.clientY;
        return point.matrixTransform(svg.getScreenCTM().inverse());
    }

    function springBack() {
        cancelAnimationFrame(springFrame);
        if (reduceMotion) { pos = { x: REST.x, y: REST.y }; draw(); return; }
        let vx = 0, vy = 0;
        (function step() {
            // ressort amorti : la perle revient à sa place en rebondissant un peu
            vx += (REST.x - pos.x) * 0.18; vy += (REST.y - pos.y) * 0.18;
            vx *= 0.72; vy *= 0.72;
            pos.x += vx; pos.y += vy;
            draw();
            if (Math.abs(pos.y - REST.y) > 0.2 || Math.abs(vy) > 0.2 || Math.abs(pos.x - REST.x) > 0.2) {
                springFrame = requestAnimationFrame(step);
            } else {
                pos = { x: REST.x, y: REST.y };
                draw();
            }
        })();
    }

    bead.addEventListener("pointerdown", function (event) {
        dragging = true; triggered = false; moved = false;
        startPointer = toSvgPoint(event);
        cancelAnimationFrame(springFrame);
        bead.setPointerCapture(event.pointerId);
        event.preventDefault();
    });

    bead.addEventListener("pointermove", function (event) {
        if (!dragging) return;
        const p = toSvgPoint(event);
        const dy = Math.max(0, Math.min(MAX_PULL, REST.y + (p.y - startPointer.y) - REST.y));
        const dx = Math.max(-12, Math.min(12, (p.x - startPointer.x) * 0.3));
        if (dy > 4) moved = true;
        pos.x = REST.x + dx;
        pos.y = REST.y + dy;
        draw();
        if (dy >= TRIGGER && !triggered) { triggered = true; toggleLamp(); }
    });

    function release(event) {
        if (!dragging) return;
        dragging = false;
        if (bead.hasPointerCapture(event.pointerId)) bead.releasePointerCapture(event.pointerId);
        // simple clic sans glisser : on allume quand même (utile sur écran tactile)
        if (!moved && !triggered) toggleLamp();
        springBack();
    }
    bead.addEventListener("pointerup", release);
    bead.addEventListener("pointercancel", release);

    // Clavier : Entrée ou Espace sur la perle
    bead.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            pos.y = REST.y + 40; draw();
            toggleLamp();
            setTimeout(springBack, 120);
        }
    });

    draw();

    // ---------- Couleur de la lumière ----------
    const dots = document.querySelectorAll(".color-dot-btn");
    function setColor(name) {
        body.dataset.color = name;
        dots.forEach(function (d) { d.classList.toggle("active", d.dataset.color === name); });
        localStorage.setItem("lampColor", name);
        recolorDust();
    }
    dots.forEach(function (dot) {
        dot.addEventListener("click", function () { setColor(dot.dataset.color); });
    });

    // ---------- Son ----------
    const soundBtn = document.getElementById("soundToggle");
    let audioCtx = null;
    function click(on) {
        if (!soundOn) return;
        try {
            audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = "square";
            osc.frequency.value = on ? 1500 : 900;
            gain.gain.setValueAtTime(0.06, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.07);
            osc.connect(gain); gain.connect(audioCtx.destination);
            osc.start(); osc.stop(audioCtx.currentTime + 0.08);
        } catch (e) { /* pas de son : tant pis */ }
    }
    function showSoundIcon() {
        soundBtn.querySelector(".sound-on").classList.toggle("hidden", !soundOn);
        soundBtn.querySelector(".sound-off").classList.toggle("hidden", soundOn);
    }
    soundBtn.addEventListener("click", function () {
        soundOn = !soundOn;
        localStorage.setItem("lampSound", soundOn ? "on" : "off");
        showSoundIcon();
    });
    showSoundIcon();

    // ---------- Afficher / masquer le mot de passe ----------
    const eye = document.getElementById("eyeToggle");
    const passField = document.getElementById("id_password");
    if (eye && passField) {
        eye.addEventListener("click", function () {
            const show = passField.type === "password";
            passField.type = show ? "text" : "password";
            eye.querySelector(".eye-show").classList.toggle("hidden", show);
            eye.querySelector(".eye-hide").classList.toggle("hidden", !show);
        });
    }

    // ---------- Poussière lumineuse ----------
    const canvas = document.getElementById("dustCanvas");
    const ctx = canvas.getContext("2d");
    let particles = [], dustFrame = null, dustColor = "255, 225, 150";

    function resizeCanvas() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
    window.addEventListener("resize", resizeCanvas);
    resizeCanvas();

    function recolorDust() {
        const glow = getComputedStyle(body).getPropertyValue("--lamp-glow").trim();
        const m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(glow);
        if (m) dustColor = parseInt(m[1], 16) + ", " + parseInt(m[2], 16) + ", " + parseInt(m[3], 16);
    }

    function newParticle() {
        return {
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            r: Math.random() * 1.8 + 0.4,
            vx: (Math.random() - 0.5) * 0.25,
            vy: -Math.random() * 0.3 - 0.05,
            a: Math.random() * 0.5 + 0.15,
            t: Math.random() * Math.PI * 2
        };
    }

    function startDust() {
        if (reduceMotion || dustFrame) return;
        recolorDust();
        particles = Array.from({ length: 70 }, newParticle);
        (function frame() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(function (p) {
                p.t += 0.02;
                p.x += p.vx + Math.sin(p.t) * 0.15;
                p.y += p.vy;
                if (p.y < -5) { p.y = canvas.height + 5; p.x = Math.random() * canvas.width; }
                if (p.x < -5) p.x = canvas.width + 5;
                if (p.x > canvas.width + 5) p.x = -5;
                ctx.beginPath();
                ctx.fillStyle = "rgba(" + dustColor + "," + (p.a * (0.6 + Math.sin(p.t) * 0.4)) + ")";
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fill();
            });
            dustFrame = requestAnimationFrame(frame);
        })();
    }
    function stopDust() {
        cancelAnimationFrame(dustFrame);
        dustFrame = null;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    // ---------- Démarrage ----------
    setColor(localStorage.getItem("lampColor") || "amber");
    // Si le formulaire revient avec des erreurs, la lampe reste allumée (data-on="true" posé par le serveur)
    if (body.dataset.on === "true") setLamp(true);
})();
