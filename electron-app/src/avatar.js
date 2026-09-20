/**
 * Luna JARVIS - Enhanced Three.js Avatar v2
 * Moon-themed avatar with orbital rings, particle trails, and expressive states.
 *
 * Features:
 * - Crescent moon with face (eyes, mouth)
 * - 3 orbital rings with particles
 * - State-reactive colors and animations
 * - Idle breathing, listening pulse, thinking spin, speaking bounce
 * - Glow aura that changes with state
 * - Star field background
 */

class LunaAvatar {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Avatar container not found:', containerId);
            return;
        }

        this.state = 'idle'; // idle, listening, thinking, speaking
        this.time = 0;
        this.targetColors = { moon: 0xe8e0f0, glow: 0x9933ff, eye: 0xcc99ff };
        this.currentColors = { ...this.targetColors };
        this.mouthOpen = 0;
        this.emotionOverride = null;
        this._targetMoonScale = { x: 1, y: 1, z: 1 };
        this._targetMoonTilt = 0;

        this._initScene();
        this._createStarField();
        this._createMoon();
        this._createFace();
        this._createOrbitalRings();
        this._createAuraGlow();
        this._createParticleTrails();
        this._animate();
    }

    _initScene() {
        const w = this.container.clientWidth || 120;
        const h = this.container.clientHeight || 140;

        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 100);
        this.camera.position.z = 3.5;

        this.renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        this.renderer.setSize(w, h);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setClearColor(0x000000, 0);
        this.container.appendChild(this.renderer.domElement);

        // Lighting
        const ambient = new THREE.AmbientLight(0x6633cc, 0.4);
        this.scene.add(ambient);

        this.mainLight = new THREE.DirectionalLight(0xcc99ff, 0.9);
        this.mainLight.position.set(3, 2, 4);
        this.scene.add(this.mainLight);

        this.pointLight = new THREE.PointLight(0x9933ff, 0.6, 8);
        this.pointLight.position.set(0, 0, 2.5);
        this.scene.add(this.pointLight);

        this.rimLight = new THREE.PointLight(0x6633ff, 0.3, 6);
        this.rimLight.position.set(-2, 1, 1);
        this.scene.add(this.rimLight);
    }

    _createStarField() {
        const count = 60;
        const geo = new THREE.BufferGeometry();
        const positions = new Float32Array(count * 3);
        const sizes = new Float32Array(count);

        for (let i = 0; i < count; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 6;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 5;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 3 - 1;
            sizes[i] = Math.random() * 2 + 0.5;
        }

        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const mat = new THREE.PointsMaterial({
            color: 0xaabbff,
            size: 0.015,
            transparent: true,
            opacity: 0.4,
            sizeAttenuation: true,
        });

        this.stars = new THREE.Points(geo, mat);
        this.scene.add(this.stars);
    }

    _createMoon() {
        // Main moon body
        const moonGeo = new THREE.SphereGeometry(0.65, 48, 48);
        const moonMat = new THREE.MeshPhongMaterial({
            color: 0xe8e0f0,
            emissive: 0x331166,
            emissiveIntensity: 0.15,
            shininess: 40,
            specular: 0x442288,
        });
        this.moon = new THREE.Mesh(moonGeo, moonMat);
        this.scene.add(this.moon);

        // Crescent shadow
        const shadowGeo = new THREE.SphereGeometry(0.62, 48, 48);
        const shadowMat = new THREE.MeshBasicMaterial({
            color: 0x0a0a18,
            transparent: true,
            opacity: 0.75,
        });
        this.shadow = new THREE.Mesh(shadowGeo, shadowMat);
        this.shadow.position.set(0.3, 0.18, 0.12);
        this.scene.add(this.shadow);

        // Crescent highlight edge
        const edgeGeo = new THREE.TorusGeometry(0.64, 0.012, 8, 64, Math.PI * 0.7);
        const edgeMat = new THREE.MeshBasicMaterial({
            color: 0xccaaff,
            transparent: true,
            opacity: 0.3,
        });
        this.crescentEdge = new THREE.Mesh(edgeGeo, edgeMat);
        this.crescentEdge.position.z = 0.01;
        this.crescentEdge.rotation.z = -0.5;
        this.scene.add(this.crescentEdge);
    }

    _createFace() {
        // Eye sockets (dark circles behind eyes)
        const socketGeo = new THREE.CircleGeometry(0.09, 16);
        const socketMat = new THREE.MeshBasicMaterial({
            color: 0x1a1025,
            transparent: true,
            opacity: 0.8,
        });

        this.leftSocket = new THREE.Mesh(socketGeo, socketMat);
        this.leftSocket.position.set(-0.18, 0.12, 0.62);
        this.scene.add(this.leftSocket);

        this.rightSocket = new THREE.Mesh(socketGeo, socketMat);
        this.rightSocket.position.set(0.12, 0.12, 0.62);
        this.scene.add(this.rightSocket);

        // Eyes (glowing spheres)
        const eyeGeo = new THREE.SphereGeometry(0.055, 16, 16);
        const eyeMat = new THREE.MeshBasicMaterial({ color: 0xcc99ff });

        this.leftEye = new THREE.Mesh(eyeGeo, eyeMat);
        this.leftEye.position.set(-0.18, 0.12, 0.64);
        this.scene.add(this.leftEye);

        this.rightEye = new THREE.Mesh(eyeGeo, eyeMat.clone());
        this.rightEye.position.set(0.12, 0.12, 0.64);
        this.scene.add(this.rightEye);

        // Pupils (dark centers)
        const pupilGeo = new THREE.SphereGeometry(0.025, 12, 12);
        const pupilMat = new THREE.MeshBasicMaterial({ color: 0x1a0033 });

        this.leftPupil = new THREE.Mesh(pupilGeo, pupilMat);
        this.leftPupil.position.set(-0.18, 0.12, 0.68);
        this.scene.add(this.leftPupil);

        this.rightPupil = new THREE.Mesh(pupilGeo, pupilMat.clone());
        this.rightPupil.position.set(0.12, 0.12, 0.68);
        this.scene.add(this.rightPupil);

        // Eye highlights (tiny white dots)
        const highlightGeo = new THREE.SphereGeometry(0.012, 8, 8);
        const highlightMat = new THREE.MeshBasicMaterial({ color: 0xffffff });

        this.leftHighlight = new THREE.Mesh(highlightGeo, highlightMat);
        this.leftHighlight.position.set(-0.16, 0.14, 0.70);
        this.scene.add(this.leftHighlight);

        this.rightHighlight = new THREE.Mesh(highlightGeo, highlightMat.clone());
        this.rightHighlight.position.set(0.14, 0.14, 0.70);
        this.scene.add(this.rightHighlight);

        // Eyelids (for blinking)
        const lidGeo = new THREE.SphereGeometry(0.07, 16, 8, 0, Math.PI * 2, 0, Math.PI * 0.5);
        const lidMat = new THREE.MeshBasicMaterial({
            color: 0x0a0a18,
            transparent: true,
            opacity: 0,
            side: THREE.DoubleSide,
        });

        this.leftLid = new THREE.Mesh(lidGeo, lidMat);
        this.leftLid.position.set(-0.18, 0.12, 0.63);
        this.leftLid.rotation.x = Math.PI;
        this.scene.add(this.leftLid);

        this.rightLid = new THREE.Mesh(lidGeo, lidMat.clone());
        this.rightLid.position.set(0.12, 0.12, 0.63);
        this.rightLid.rotation.x = Math.PI;
        this.scene.add(this.rightLid);

        // Mouth (curved line using torus segment)
        const mouthGeo = new THREE.TorusGeometry(0.06, 0.008, 8, 16, Math.PI * 0.6);
        const mouthMat = new THREE.MeshBasicMaterial({
            color: 0xcc99ff,
            transparent: true,
            opacity: 0.7,
        });
        this.mouth = new THREE.Mesh(mouthGeo, mouthMat);
        this.mouth.position.set(-0.03, -0.05, 0.64);
        this.mouth.rotation.z = Math.PI;
        this.scene.add(this.mouth);

        // Blush circles
        const blushGeo = new THREE.CircleGeometry(0.04, 12);
        const blushMat = new THREE.MeshBasicMaterial({
            color: 0xff6699,
            transparent: true,
            opacity: 0.0,
        });

        this.leftBlush = new THREE.Mesh(blushGeo, blushMat);
        this.leftBlush.position.set(-0.28, 0.0, 0.60);
        this.scene.add(this.leftBlush);

        this.rightBlush = new THREE.Mesh(blushGeo, blushMat.clone());
        this.rightBlush.position.set(0.22, 0.0, 0.60);
        this.scene.add(this.rightBlush);
    }

    _createOrbitalRings() {
        this.orbitalRings = [];
        const ringConfigs = [
            { radius: 0.95, tilt: 0.3, speed: 0.2, color: 0x9933ff, particles: 20, opacity: 0.15 },
            { radius: 1.15, tilt: -0.5, speed: -0.15, color: 0x6644cc, particles: 15, opacity: 0.1 },
            { radius: 1.35, tilt: 0.8, speed: 0.1, color: 0x3366ff, particles: 12, opacity: 0.08 },
        ];

        for (const cfg of ringConfigs) {
            const group = new THREE.Group();

            // Ring line
            const ringGeo = new THREE.TorusGeometry(cfg.radius, 0.008, 4, 80);
            const ringMat = new THREE.MeshBasicMaterial({
                color: cfg.color,
                transparent: true,
                opacity: cfg.opacity,
            });
            const ring = new THREE.Mesh(ringGeo, ringMat);
            group.add(ring);

            // Particles on ring
            const particleGeo = new THREE.BufferGeometry();
            const positions = new Float32Array(cfg.particles * 3);
            for (let i = 0; i < cfg.particles; i++) {
                const angle = (i / cfg.particles) * Math.PI * 2;
                positions[i * 3] = Math.cos(angle) * cfg.radius;
                positions[i * 3 + 1] = Math.sin(angle) * cfg.radius;
                positions[i * 3 + 2] = 0;
            }
            particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

            const particleMat = new THREE.PointsMaterial({
                color: cfg.color,
                size: 0.03,
                transparent: true,
                opacity: 0.5,
                sizeAttenuation: true,
            });
            const particles = new THREE.Points(particleGeo, particleMat);
            group.add(particles);

            group.rotation.x = cfg.tilt;
            group.rotation.y = Math.random() * Math.PI;

            this.scene.add(group);
            this.orbitalRings.push({ group, config: cfg, particles });
        }
    }

    _createAuraGlow() {
        // Inner glow sphere
        const innerGeo = new THREE.SphereGeometry(0.72, 32, 32);
        const innerMat = new THREE.MeshBasicMaterial({
            color: 0x9933ff,
            transparent: true,
            opacity: 0.05,
        });
        this.innerGlow = new THREE.Mesh(innerGeo, innerMat);
        this.scene.add(this.innerGlow);

        // Outer glow sphere
        const outerGeo = new THREE.SphereGeometry(0.85, 32, 32);
        const outerMat = new THREE.MeshBasicMaterial({
            color: 0x6633cc,
            transparent: true,
            opacity: 0.03,
        });
        this.outerGlow = new THREE.Mesh(outerGeo, outerMat);
        this.scene.add(this.outerGlow);

        // Glow ring around moon
        const glowRingGeo = new THREE.RingGeometry(0.7, 0.9, 48);
        const glowRingMat = new THREE.MeshBasicMaterial({
            color: 0x9933ff,
            transparent: true,
            opacity: 0.1,
            side: THREE.DoubleSide,
        });
        this.glowRing = new THREE.Mesh(glowRingGeo, glowRingMat);
        this.glowRing.position.z = 0.01;
        this.scene.add(this.glowRing);
    }

    _createParticleTrails() {
        this.trails = [];
        const trailCount = 25;
        const geo = new THREE.BufferGeometry();
        const positions = new Float32Array(trailCount * 3);
        const velocities = [];

        for (let i = 0; i < trailCount; i++) {
            const angle = Math.random() * Math.PI * 2;
            const radius = 0.8 + Math.random() * 0.6;
            positions[i * 3] = Math.cos(angle) * radius;
            positions[i * 3 + 1] = Math.sin(angle) * radius;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 0.5;
            velocities.push({
                angle: angle,
                radius: radius,
                speed: 0.002 + Math.random() * 0.003,
                yOffset: Math.random() * Math.PI * 2,
                zOffset: (Math.random() - 0.5) * 0.3,
            });
        }

        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const mat = new THREE.PointsMaterial({
            color: 0xcc88ff,
            size: 0.02,
            transparent: true,
            opacity: 0.4,
            sizeAttenuation: true,
        });

        this.trailSystem = new THREE.Points(geo, mat);
        this.trailVelocities = velocities;
        this.scene.add(this.trailSystem);
    }

    // ── Emotion Colors ──────────────────────────────────────────

    static EMOTION_COLORS = {
        'happy':     { moon: 0xfff0d0, glow: 0xffcc33, eye: 0xffdd66, mouth: 0.5, blush: 0.25 },
        'excited':   { moon: 0xffe0d0, glow: 0xff6633, eye: 0xff9966, mouth: 0.7, blush: 0.3  },
        'sad':       { moon: 0xd0d8f0, glow: 0x4466cc, eye: 0x7799dd, mouth: 0,   blush: 0    },
        'frustrated':{ moon: 0xf0d8d0, glow: 0xcc4433, eye: 0xdd6655, mouth: 0,   blush: 0.1  },
        'angry':     { moon: 0xf0d0d0, glow: 0xff2222, eye: 0xff4444, mouth: 0,   blush: 0.2  },
        'anxious':   { moon: 0xe8ddf0, glow: 0x9944cc, eye: 0xbb77dd, mouth: 0.1, blush: 0.05 },
        'tired':     { moon: 0xdde0e8, glow: 0x667799, eye: 0x8899bb, mouth: 0,   blush: 0    },
        'curious':   { moon: 0xd8f0e8, glow: 0x33cc88, eye: 0x66ddaa, mouth: 0.2, blush: 0.05 },
        'confused':  { moon: 0xe8e0f0, glow: 0x8866cc, eye: 0xaa88dd, mouth: 0.1, blush: 0    },
        'grateful':  { moon: 0xfff0e8, glow: 0xff8866, eye: 0xffaa88, mouth: 0.4, blush: 0.3  },
        'sarcastic': { moon: 0xf0e8f0, glow: 0xcc66ff, eye: 0xdd88ff, mouth: 0.3, blush: 0.15 },
        'neutral':   null, // falls back to state-based colors
    };

    // ── State Management ────────────────────────────────────────

    setState(newState) {
        if (this.state === newState && !this.emotionOverride) return;
        this.state = newState;
        this.emotionOverride = null;
        this._updateVisuals();
    }

    /**
     * Set emotion-based avatar appearance.
     * Pass null or 'neutral' to clear emotion override.
     */
    setEmotion(emotionName, intensity) {
        if (!emotionName || emotionName === 'neutral') {
            this.emotionOverride = null;
            this._updateVisuals();
            return;
        }
        const colors = LunaAvatar.EMOTION_COLORS[emotionName];
        if (!colors) return;

        // Scale effect by intensity (0.0-1.0)
        const t = (typeof intensity === 'number') ? Math.max(0.2, Math.min(1, intensity)) : 0.7;

        this.emotionOverride = colors;
        this.targetColors = { moon: colors.moon, glow: colors.glow, eye: colors.eye };
        this.mouthTarget = colors.mouth * t;
        this.blushTarget = colors.blush * t;
        this._emotionIntensity = t;

        // Emotion-specific shape changes (scaled by intensity)
        this._applyEmotionShape(emotionName);
    }

    _applyEmotionShape(emotion) {
        // Subtle shape morphing based on emotion, scaled by intensity
        if (!this.moon) return;
        const t = this._emotionIntensity || 0.7;
        switch (emotion) {
            case 'happy':
            case 'grateful':
                // Slightly wider, cheerful
                this._targetMoonScale = { x: 1 + 0.04 * t, y: 1 - 0.03 * t, z: 1.0 };
                break;
            case 'sad':
            case 'tired':
                // Slightly droopy
                this._targetMoonScale = { x: 1 - 0.03 * t, y: 1 + 0.04 * t, z: 1.0 };
                break;
            case 'angry':
            case 'frustrated':
                // Slightly wider, tense
                this._targetMoonScale = { x: 1 + 0.06 * t, y: 1 - 0.05 * t, z: 1.0 };
                break;
            case 'excited':
                // Bigger, energetic
                this._targetMoonScale = { x: 1 + 0.05 * t, y: 1 + 0.05 * t, z: 1.0 };
                break;
            case 'curious':
                // Slightly tilted
                this._targetMoonScale = { x: 1.0, y: 1.0, z: 1.0 };
                this._targetMoonTilt = 0.1 * t;
                break;
            default:
                this._targetMoonScale = { x: 1.0, y: 1.0, z: 1.0 };
                this._targetMoonTilt = 0;
                break;
        }
    }

    _updateVisuals() {
        if (this.emotionOverride) {
            // Emotion colors are already set in setEmotion()
            return;
        }
        switch (this.state) {
            case 'idle':
                this.targetColors = { moon: 0xe8e0f0, glow: 0x9933ff, eye: 0xcc99ff };
                this.mouthTarget = 0;
                this.blushTarget = 0;
                break;
            case 'listening':
                this.targetColors = { moon: 0xf0dde0, glow: 0xff3366, eye: 0xff66aa };
                this.mouthTarget = 0.3;
                this.blushTarget = 0.15;
                break;
            case 'thinking':
                this.targetColors = { moon: 0xdde0f0, glow: 0x3366ff, eye: 0x6699ff };
                this.mouthTarget = 0;
                this.blushTarget = 0;
                break;
            case 'speaking':
                this.targetColors = { moon: 0xe0f0e5, glow: 0x33ff88, eye: 0x66ffaa };
                this.mouthTarget = 0.5;
                this.blushTarget = 0.1;
                break;
        }
        this._targetMoonScale = { x: 1.0, y: 1.0, z: 1.0 };
        this._targetMoonTilt = 0;
    }

    _lerpColor(current, target, speed) {
        const c = new THREE.Color(current);
        const t = new THREE.Color(target);
        c.lerp(t, speed);
        return c.getHex();
    }

    _lerp(a, b, speed) {
        return a + (b - a) * speed;
    }

    // ── Animation Loop ──────────────────────────────────────────

    _animate() {
        requestAnimationFrame(() => this._animate());
        const dt = 0.016;
        this.time += dt;
        const speed = 0.05;

        // Smooth color transitions
        this.currentColors.moon = this._lerpColor(this.currentColors.moon, this.targetColors.moon, speed);
        this.currentColors.glow = this._lerpColor(this.currentColors.glow, this.targetColors.glow, speed);
        this.currentColors.eye = this._lerpColor(this.currentColors.eye, this.targetColors.eye, speed);
        this.mouthOpen = this._lerp(this.mouthOpen, this.mouthTarget, speed);

        // Apply colors
        if (this.moon) {
            this.moon.material.color.setHex(this.currentColors.moon);
        }
        if (this.leftEye) this.leftEye.material.color.setHex(this.currentColors.eye);
        if (this.rightEye) this.rightEye.material.color.setHex(this.currentColors.eye);
        if (this.innerGlow) this.innerGlow.material.color.setHex(this.currentColors.glow);
        if (this.glowRing) this.glowRing.material.color.setHex(this.currentColors.glow);
        if (this.pointLight) this.pointLight.color.setHex(this.currentColors.glow);

        // ── Moon breathing ──
        if (this.moon) {
            const breathe = Math.sin(this.time * 1.2) * 0.008;
            // Apply emotion-based shape morphing
            const targetScale = this._targetMoonScale || { x: 1, y: 1, z: 1 };
            const scaleSpeed = 0.03;
            this.moon.scale.x = this._lerp(this.moon.scale.x, targetScale.x + breathe, scaleSpeed);
            this.moon.scale.y = this._lerp(this.moon.scale.y, targetScale.y + breathe, scaleSpeed);
            this.moon.scale.z = this._lerp(this.moon.scale.z, targetScale.z + breathe, scaleSpeed);
            this.moon.rotation.y = Math.sin(this.time * 0.4) * 0.08;
            // Emotion tilt (curious → slight head tilt)
            const targetTilt = this._targetMoonTilt || 0;
            this.moon.rotation.x = this._lerp(this.moon.rotation.x, Math.cos(this.time * 0.3) * 0.04 + targetTilt, scaleSpeed);
        }

        // ── Eye tracking (subtle look-around) ──
        const lookX = Math.sin(this.time * 0.7) * 0.02;
        const lookY = Math.cos(this.time * 0.5) * 0.015;
        if (this.leftPupil) {
            this.leftPupil.position.x = -0.18 + lookX;
            this.leftPupil.position.y = 0.12 + lookY;
        }
        if (this.rightPupil) {
            this.rightPupil.position.x = 0.12 + lookX;
            this.rightPupil.position.y = 0.12 + lookY;
        }

        // ── Blinking ──
        const blinkCycle = this.time % 4;
        let blinkAmount = 0;
        if (blinkCycle > 3.7 && blinkCycle < 3.85) {
            blinkAmount = Math.sin((blinkCycle - 3.7) / 0.15 * Math.PI);
        }
        if (this.leftLid) this.leftLid.material.opacity = blinkAmount * 0.95;
        if (this.rightLid) this.rightLid.material.opacity = blinkAmount * 0.95;

        // ── Mouth animation ──
        if (this.mouth) {
            this.mouth.scale.y = 1 + this.mouthOpen * 2;
            this.mouth.material.opacity = 0.5 + this.mouthOpen * 0.3;
        }

        // ── Blush ──
        if (this.leftBlush) {
            const currentBlush = this.leftBlush.material.opacity;
            this.leftBlush.material.opacity = this._lerp(currentBlush, this.blushTarget, speed);
            this.rightBlush.material.opacity = this._lerp(currentBlush, this.blushTarget, speed);
        }

        // ── Orbital rings ──
        for (const ring of this.orbitalRings) {
            ring.group.rotation.z += ring.config.speed * dt;
            // Subtle wobble
            ring.group.rotation.x = ring.config.tilt + Math.sin(this.time * 0.5) * 0.05;
        }

        // ── Aura glow pulse (emotion intensity affects brightness) ──
        if (this.innerGlow) {
            const emoBoost = (this.emotionOverride && this._emotionIntensity) ? this._emotionIntensity * 0.04 : 0;
            const pulse = 0.04 + emoBoost + Math.sin(this.time * 1.5) * 0.02;
            this.innerGlow.material.opacity = pulse;
            this.innerGlow.scale.setScalar(1 + Math.sin(this.time * 2) * 0.03 + emoBoost * 2);
        }
        if (this.outerGlow) {
            const emoBoost = (this.emotionOverride && this._emotionIntensity) ? this._emotionIntensity * 0.015 : 0;
            this.outerGlow.material.opacity = 0.02 + emoBoost + Math.sin(this.time * 1) * 0.01;
        }
        if (this.glowRing) {
            const emoBoost = (this.emotionOverride && this._emotionIntensity) ? this._emotionIntensity * 0.03 : 0;
            const ringPulse = 1 + Math.sin(this.time * 1.8) * (0.04 + emoBoost);
            this.glowRing.scale.set(ringPulse, ringPulse, 1);
        }

        // ── Star twinkle ──
        if (this.stars) {
            this.stars.rotation.y = this.time * 0.01;
            this.stars.material.opacity = 0.3 + Math.sin(this.time * 0.8) * 0.1;
        }

        // ── Particle trails ──
        if (this.trailSystem) {
            const positions = this.trailSystem.geometry.attributes.position.array;
            for (let i = 0; i < this.trailVelocities.length; i++) {
                const v = this.trailVelocities[i];
                v.angle += v.speed;
                const wobble = Math.sin(this.time * 2 + v.yOffset) * 0.05;
                positions[i * 3] = Math.cos(v.angle) * (v.radius + wobble);
                positions[i * 3 + 1] = Math.sin(v.angle) * (v.radius + wobble);
                positions[i * 3 + 2] = v.zOffset + Math.sin(this.time + i) * 0.05;
            }
            this.trailSystem.geometry.attributes.position.needsUpdate = true;
            this.trailSystem.material.opacity = 0.3 + Math.sin(this.time * 1.2) * 0.1;
        }

        // ── State-specific animations ──
        this._applyStateAnimation();

        this.renderer.render(this.scene, this.camera);
    }

    _applyStateAnimation() {
        switch (this.state) {
            case 'listening':
                // Rapid glow pulse
                if (this.glowRing) {
                    this.glowRing.material.opacity = 0.15 + Math.sin(this.time * 5) * 0.12;
                }
                // Eyes widen slightly
                if (this.leftEye) {
                    this.leftEye.scale.setScalar(1.1 + Math.sin(this.time * 3) * 0.05);
                    this.rightEye.scale.setScalar(1.1 + Math.sin(this.time * 3) * 0.05);
                }
                break;

            case 'thinking':
                // Orbital rings spin faster
                for (const ring of this.orbitalRings) {
                    ring.group.rotation.z += 0.01;
                }
                // Eyes look up
                if (this.leftPupil) {
                    this.leftPupil.position.y = 0.14 + Math.sin(this.time * 2) * 0.01;
                    this.rightPupil.position.y = 0.14 + Math.sin(this.time * 2) * 0.01;
                }
                break;

            case 'speaking':
                // Mouth opens/closes rhythmically
                if (this.mouth) {
                    this.mouth.scale.y = 1 + Math.abs(Math.sin(this.time * 8)) * 1.5;
                }
                // Gentle bounce
                if (this.moon) {
                    this.moon.position.y = Math.sin(this.time * 4) * 0.02;
                }
                // Brighter glow
                if (this.innerGlow) {
                    this.innerGlow.material.opacity = 0.08 + Math.sin(this.time * 3) * 0.04;
                }
                break;

            default:
                // Reset eye scale
                if (this.leftEye) {
                    this.leftEye.scale.setScalar(1);
                    this.rightEye.scale.setScalar(1);
                }
                if (this.moon) {
                    this.moon.position.y = 0;
                }
                break;
        }
    }

    // ── Cleanup ─────────────────────────────────────────────────

    destroy() {
        if (this.renderer) {
            this.renderer.dispose();
            if (this.container && this.renderer.domElement) {
                this.container.removeChild(this.renderer.domElement);
            }
        }
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LunaAvatar;
}
