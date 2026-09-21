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
        this._lastBurstEmotion = null;

        // Cursor eye tracking (session 36)
        this._mouseX = 0;
        this._mouseY = 0;
        this._eyeTrackingEnabled = true;
        this._eyeTrackSmoothX = 0;
        this._eyeTrackSmoothY = 0;

        // TTS mouth sync (session 36)
        this._mouthSyncActive = false;
        this._mouthSyncAmplitude = 0;
        this._mouthSyncTarget = 0;

        this._initScene();
        this._createStarField();
        this._createMoon();
        this._createFace();
        this._createOrbitalRings();
        this._createAuraGlow();
        this._createParticleTrails();
        this._setupCursorTracking();
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
        this._trailTargetColor = 0xcc88ff;  // Default trail color
        this._trailCurrentColor = 0xcc88ff;
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
        'surprised': { moon: 0xf0e8ff, glow: 0xee88ff, eye: 0xdd99ff, mouth: 0.9, blush: 0.1 },
        'embarrassed':{ moon: 0xf0dde8, glow: 0xff6699, eye: 0xff88aa, mouth: 0.15, blush: 0.4 },
        'neutral':   null, // falls back to state-based colors
    };

    // Compound emotion blend profiles (Session 38)
    // Blends two emotions' visual properties with a "flavor" override
    static COMPOUND_PROFILES = {
        'delight':    { moonBlend: 0.6, glowColor: 0xffaa44, eyeColor: 0xffcc66, mouthMul: 1.2, blushMul: 0.8, scaleBoost: 0.08 },
        'shy_joy':    { moonBlend: 0.5, glowColor: 0xff88aa, eyeColor: 0xffaacc, mouthMul: 0.7, blushMul: 1.5, scaleBoost: -0.02 },
        'bitter':     { moonBlend: 0.5, glowColor: 0x884455, eyeColor: 0xaa6677, mouthMul: 0.3, blushMul: 0.5, scaleBoost: 0.02 },
        'amazed':     { moonBlend: 0.5, glowColor: 0xaa66ff, eyeColor: 0xcc88ff, mouthMul: 1.3, blushMul: 0.3, scaleBoost: 0.1 },
        'playful':    { moonBlend: 0.5, glowColor: 0x88dd66, eyeColor: 0xaaff88, mouthMul: 0.8, blushMul: 0.6, scaleBoost: 0.03 },
        'vulnerable': { moonBlend: 0.5, glowColor: 0x9977aa, eyeColor: 0xbb99cc, mouthMul: 0.5, blushMul: 1.2, scaleBoost: -0.04 },
        'shocked':    { moonBlend: 0.5, glowColor: 0xff4466, eyeColor: 0xff6688, mouthMul: 1.4, blushMul: 0.4, scaleBoost: 0.12 },
        'joyful':     { moonBlend: 0.6, glowColor: 0xffaa66, eyeColor: 0xffcc88, mouthMul: 1.1, blushMul: 1.0, scaleBoost: 0.06 },
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
     * Supports compound emotions via compoundInfo parameter (Session 38).
     */
    setEmotion(emotionName, intensity, compoundInfo) {
        if (!emotionName || emotionName === 'neutral') {
            this.emotionOverride = null;
            this._compoundProfile = null;
            this._updateVisuals();
            return;
        }
        const colors = LunaAvatar.EMOTION_COLORS[emotionName];
        if (!colors) return;

        // Scale effect by intensity (0.0-1.0)
        const t = (typeof intensity === 'number') ? Math.max(0.2, Math.min(1, intensity)) : 0.7;

        // Check for compound emotion profile (Session 38)
        if (compoundInfo && compoundInfo.name) {
            const profile = LunaAvatar.COMPOUND_PROFILES[compoundInfo.name];
            if (profile) {
                this._compoundProfile = profile;
                // Blend colors with compound profile
                this.targetColors = {
                    moon: this._lerpColorValue(colors.moon, profile.glowColor, 0.3),
                    glow: profile.glowColor,
                    eye: profile.eyeColor,
                };
                this.mouthTarget = colors.mouth * t * profile.mouthMul;
                this.blushTarget = colors.blush * t * profile.blushMul;
                this._emotionIntensity = t;
                this.emotionOverride = colors;
                // Apply compound shape
                this._applyCompoundShape(emotionName, profile, t);
                // Trigger burst for compound too
                if (t > 0.6 && this._lastBurstEmotion !== compoundInfo.name) {
                    this.triggerEmotionBurst(emotionName);
                    this._lastBurstEmotion = compoundInfo.name;
                }
                return;
            }
        }

        this._compoundProfile = null;
        this.emotionOverride = colors;
        this.targetColors = { moon: colors.moon, glow: colors.glow, eye: colors.eye };
        this.mouthTarget = colors.mouth * t;
        this.blushTarget = colors.blush * t;
        this._emotionIntensity = t;

        // Trigger particle burst for strong emotions
        if (t > 0.7 && this._lastBurstEmotion !== emotionName) {
            this.triggerEmotionBurst(emotionName);
            this._lastBurstEmotion = emotionName;
        }
        if (t <= 0.5) {
            this._lastBurstEmotion = null;
        }

        // Emotion-specific shape changes (scaled by intensity)
        this._applyEmotionShape(emotionName);
    }

    _applyCompoundShape(emotionName, profile, t) {
        if (!this.moon) return;
        const boost = profile.scaleBoost || 0;
        this._targetMoonScale = { x: 1 + boost * t, y: 1 + boost * t, z: 1.0 };
        this._targetMoonTilt = 0;
        // Compound-specific tilt
        if (profile === LunaAvatar.COMPOUND_PROFILES.shy_joy || profile === LunaAvatar.COMPOUND_PROFILES.vulnerable) {
            this._targetMoonTilt = -0.06 * t; // tilt down (shy)
        } else if (profile === LunaAvatar.COMPOUND_PROFILES.amazed) {
            this._targetMoonTilt = 0.08 * t; // tilt up (amazed)
        }
    }

    /**
     * Helper: lerp between two hex color values.
     */
    _lerpColorValue(a, b, t) {
        const c = new THREE.Color(a);
        const target = new THREE.Color(b);
        c.lerp(target, t);
        return c.getHex();
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
            case 'surprised':
                // Eyes wide, bigger
                this._targetMoonScale = { x: 1 + 0.06 * t, y: 1 + 0.06 * t, z: 1.0 };
                this._targetMoonTilt = 0;
                break;
            case 'embarrassed':
                // Slightly smaller, tilted down
                this._targetMoonScale = { x: 1 - 0.02 * t, y: 1 - 0.02 * t, z: 1.0 };
                this._targetMoonTilt = -0.08 * t;
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

        // ── Eye tracking (cursor follow or idle look-around) ──
        if (this._eyeTrackingEnabled && (this._mouseX !== 0 || this._mouseY !== 0)) {
            // Smooth cursor following
            const trackSpeed = 0.08;
            this._eyeTrackSmoothX = this._lerp(this._eyeTrackSmoothX, this._mouseX, trackSpeed);
            this._eyeTrackSmoothY = this._lerp(this._eyeTrackSmoothY, this._mouseY, trackSpeed);
            const lookX = this._eyeTrackSmoothX * 0.035; // Max pupil displacement
            const lookY = this._eyeTrackSmoothY * 0.025;
            if (this.leftPupil) {
                this.leftPupil.position.x = -0.18 + lookX;
                this.leftPupil.position.y = 0.12 + lookY;
            }
            if (this.rightPupil) {
                this.rightPupil.position.x = 0.12 + lookX;
                this.rightPupil.position.y = 0.12 + lookY;
            }
            // Also subtly move the highlight
            if (this.leftHighlight) {
                this.leftHighlight.position.x = -0.16 + lookX * 0.5;
                this.leftHighlight.position.y = 0.14 + lookY * 0.5;
            }
            if (this.rightHighlight) {
                this.rightHighlight.position.x = 0.14 + lookX * 0.5;
                this.rightHighlight.position.y = 0.14 + lookY * 0.5;
            }
        } else {
            // Default idle look-around
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
        }

        // ── Blinking ──
        const blinkCycle = this.time % 4;
        let blinkAmount = 0;
        if (blinkCycle > 3.7 && blinkCycle < 3.85) {
            blinkAmount = Math.sin((blinkCycle - 3.7) / 0.15 * Math.PI);
        }
        if (this.leftLid) this.leftLid.material.opacity = blinkAmount * 0.95;
        if (this.rightLid) this.rightLid.material.opacity = blinkAmount * 0.95;

        // ── Mouth animation (TTS sync or state-based) ──
        if (this.mouth) {
            if (this._mouthSyncActive) {
                // Smooth amplitude following for TTS sync
                const syncSpeed = 0.15;
                this._mouthSyncAmplitude = this._lerp(
                    this._mouthSyncAmplitude, this._mouthSyncTarget, syncSpeed
                );
                // Map amplitude to mouth scale: 0 = closed, 1 = wide open
                this.mouthOpen = this._mouthSyncAmplitude;
                this.mouth.scale.y = 1 + this.mouthOpen * 2.5;
                this.mouth.material.opacity = 0.5 + this.mouthOpen * 0.4;
            } else {
                // Normal emotion/state-based mouth
                this.mouthOpen = this._lerp(this.mouthOpen, this.mouthTarget, speed);
                this.mouth.scale.y = 1 + this.mouthOpen * 2;
                this.mouth.material.opacity = 0.5 + this.mouthOpen * 0.3;
            }
        }

        // ── Blush ──
        if (this.leftBlush) {
            const currentBlush = this.leftBlush.material.opacity;
            this.leftBlush.material.opacity = this._lerp(currentBlush, this.blushTarget, speed);
            this.rightBlush.material.opacity = this._lerp(currentBlush, this.blushTarget, speed);
        }

        // ── Orbital rings (emotion-reactive colors) ──
        for (let ri = 0; ri < this.orbitalRings.length; ri++) {
            const ring = this.orbitalRings[ri];
            ring.group.rotation.z += ring.config.speed * dt;
            // Subtle wobble
            ring.group.rotation.x = ring.config.tilt + Math.sin(this.time * 0.5) * 0.05;
            // Emotion-reactive ring color: blend toward emotion glow
            if (this.emotionOverride && this._emotionIntensity) {
                const ringTarget = this.emotionOverride.glow;
                if (!ring._currentColor) ring._currentColor = ring.config.color;
                ring._currentColor = this._lerpColor(ring._currentColor, ringTarget, 0.02 + ri * 0.005);
                // Update ring mesh
                const ringMesh = ring.group.children[0];
                if (ringMesh && ringMesh.material) ringMesh.material.color.setHex(ring._currentColor);
                // Update particles on ring
                const ringParticles = ring.group.children[1];
                if (ringParticles && ringParticles.material) ringParticles.material.color.setHex(ring._currentColor);
            } else {
                // Reset to default
                if (ring._currentColor && ring._currentColor !== ring.config.color) {
                    ring._currentColor = this._lerpColor(ring._currentColor, ring.config.color, 0.02);
                    const ringMesh = ring.group.children[0];
                    if (ringMesh && ringMesh.material) ringMesh.material.color.setHex(ring._currentColor);
                    const ringParticles = ring.group.children[1];
                    if (ringParticles && ringParticles.material) ringParticles.material.color.setHex(ring._currentColor);
                }
            }
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

        // ── Star twinkle (emotion-reactive tint) ──
        if (this.stars) {
            this.stars.rotation.y = this.time * 0.01;
            this.stars.material.opacity = 0.3 + Math.sin(this.time * 0.8) * 0.1;
            // Stars tint toward emotion color for subtle mood shift
            if (this.emotionOverride && this._emotionIntensity) {
                if (!this._starTargetColor) this._starTargetColor = 0xaabbff;
                this._starTargetColor = this._lerpColor(this._starTargetColor, this.emotionOverride.glow, 0.008);
                this.stars.material.color.setHex(this._starTargetColor);
            } else if (this._starTargetColor && this._starTargetColor !== 0xaabbff) {
                this._starTargetColor = this._lerpColor(this._starTargetColor, 0xaabbff, 0.008);
                this.stars.material.color.setHex(this._starTargetColor);
            }
        }

        // ── Particle trails (emotion-reactive colors + shapes) ──
        if (this.trailSystem) {
            const positions = this.trailSystem.geometry.attributes.position.array;
            // Emotion-specific trail behavior (session 34)
            let trailSpeedMul = 1.0;
            let trailWobbleMul = 1.0;
            let trailRadiusDrift = 0;
            if (this.emotionOverride && this._emotionIntensity) {
                const t = this._emotionIntensity;
                if (this._lastBurstEmotion === 'happy' || this._lastBurstEmotion === 'grateful') {
                    trailSpeedMul = 1.0 + 0.3 * t;  // faster sparkle
                    trailWobbleMul = 1.0 + 0.5 * t;  // more wobble
                } else if (this._lastBurstEmotion === 'sad' || this._lastBurstEmotion === 'tired') {
                    trailSpeedMul = 1.0 - 0.4 * t;  // slower
                    trailWobbleMul = 1.0 - 0.3 * t;  // calmer
                    trailRadiusDrift = -0.01 * t;     // drift inward
                } else if (this._lastBurstEmotion === 'angry' || this._lastBurstEmotion === 'frustrated') {
                    trailSpeedMul = 1.0 + 0.5 * t;  // faster, erratic
                    trailWobbleMul = 1.0 + 0.8 * t;  // much more wobble
                } else if (this._lastBurstEmotion === 'curious') {
                    trailSpeedMul = 1.0 + 0.15 * t; // slightly faster
                    trailWobbleMul = 1.0 + 0.4 * t;  // exploring
                    trailRadiusDrift = 0.02 * t;      // drift outward
                } else if (this._lastBurstEmotion === 'excited') {
                    trailSpeedMul = 1.0 + 0.6 * t;  // very fast
                    trailWobbleMul = 1.0 + 0.6 * t;  // energetic
                }
            }
            for (let i = 0; i < this.trailVelocities.length; i++) {
                const v = this.trailVelocities[i];
                v.angle += v.speed * trailSpeedMul;
                const wobble = Math.sin(this.time * 2 + v.yOffset) * 0.05 * trailWobbleMul;
                const r = v.radius + trailRadiusDrift;
                positions[i * 3] = Math.cos(v.angle) * (r + wobble);
                positions[i * 3 + 1] = Math.sin(v.angle) * (r + wobble);
                positions[i * 3 + 2] = v.zOffset + Math.sin(this.time + i) * 0.05;
            }
            this.trailSystem.geometry.attributes.position.needsUpdate = true;
            // Emotion-reactive trail color: blend toward emotion glow color
            if (this.emotionOverride && this._emotionIntensity) {
                this._trailTargetColor = this.emotionOverride.glow;
            } else {
                this._trailTargetColor = 0xcc88ff;  // Default purple
            }
            this._trailCurrentColor = this._lerpColor(this._trailCurrentColor, this._trailTargetColor, 0.03);
            this.trailSystem.material.color.setHex(this._trailCurrentColor);
            this.trailSystem.material.opacity = 0.3 + Math.sin(this.time * 1.2) * 0.1;
        }

        // ── Emotion-specific eye effects ──
        this._applyEmotionEyeEffects();

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
                // If TTS sync is active, let it drive the mouth
                // Otherwise, use rhythmic animation
                if (!this._mouthSyncActive && this.mouth) {
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

    // ── Emotion-Specific Eye Effects ──────────────────────────────

    _applyEmotionEyeEffects() {
        if (!this.emotionOverride || !this._emotionIntensity) return;
        const t = this._emotionIntensity;
        const emo = this.emotionOverride;

        // Happy / Grateful: Sparkle eyes (scale up, add shimmer)
        if (this._lastBurstEmotion === 'happy' || this._lastBurstEmotion === 'grateful' ||
            this.emotionOverride === LunaAvatar.EMOTION_COLORS['happy'] ||
            this.emotionOverride === LunaAvatar.EMOTION_COLORS['grateful']) {
            if (this.leftEye) {
                const sparkle = 1.0 + Math.sin(this.time * 6) * 0.08 * t;
                this.leftEye.scale.setScalar(sparkle);
                this.rightEye.scale.setScalar(sparkle);
            }
            // Highlight shimmer
            if (this.leftHighlight) {
                const shimmer = 0.012 + Math.sin(this.time * 8) * 0.006 * t;
                this.leftHighlight.scale.setScalar(shimmer / 0.012);
                this.rightHighlight.scale.setScalar(shimmer / 0.012);
            }
        }
        // Sad / Tired: Droopy eyes (pupils shift down, eyes narrow)
        else if (this.emotionOverride === LunaAvatar.EMOTION_COLORS['sad'] ||
                 this.emotionOverride === LunaAvatar.EMOTION_COLORS['tired']) {
            if (this.leftPupil) {
                this.leftPupil.position.y = 0.12 - 0.015 * t + Math.sin(this.time * 0.8) * 0.003;
                this.rightPupil.position.y = 0.12 - 0.015 * t + Math.sin(this.time * 0.8) * 0.003;
            }
            if (this.leftEye) {
                this.leftEye.scale.y = 1 - 0.15 * t;
                this.rightEye.scale.y = 1 - 0.15 * t;
            }
        }
        // Angry / Frustrated: Narrowed eyes, pupils shrink
        else if (this.emotionOverride === LunaAvatar.EMOTION_COLORS['angry'] ||
                 this.emotionOverride === LunaAvatar.EMOTION_COLORS['frustrated']) {
            if (this.leftEye) {
                this.leftEye.scale.y = 1 - 0.2 * t;
                this.rightEye.scale.y = 1 - 0.2 * t;
                this.leftEye.scale.x = 1 + 0.05 * t;
                this.rightEye.scale.x = 1 + 0.05 * t;
            }
            if (this.leftPupil) {
                this.leftPupil.scale.setScalar(1 - 0.2 * t);
                this.rightPupil.scale.setScalar(1 - 0.2 * t);
            }
        }
        // Curious: Wide eyes, pupils look up-right
        else if (this.emotionOverride === LunaAvatar.EMOTION_COLORS['curious']) {
            if (this.leftPupil) {
                this.leftPupil.position.x = -0.18 + 0.02 * t + Math.sin(this.time * 1.5) * 0.01;
                this.leftPupil.position.y = 0.12 + 0.02 * t;
                this.rightPupil.position.x = 0.12 + 0.02 * t + Math.sin(this.time * 1.5) * 0.01;
                this.rightPupil.position.y = 0.12 + 0.02 * t;
            }
            if (this.leftEye) {
                this.leftEye.scale.setScalar(1 + 0.1 * t);
                this.rightEye.scale.setScalar(1 + 0.1 * t);
            }
        }
        // Excited: Big sparkling eyes
        else if (this.emotionOverride === LunaAvatar.EMOTION_COLORS['excited']) {
            if (this.leftEye) {
                const pulse = 1.1 + Math.sin(this.time * 10) * 0.06 * t;
                this.leftEye.scale.setScalar(pulse);
                this.rightEye.scale.setScalar(pulse);
            }
        }
        // Surprised: Very wide eyes, pupils shrink
        else if (this.emotionOverride === LunaAvatar.EMOTION_COLORS['surprised']) {
            if (this.leftEye) {
                this.leftEye.scale.setScalar(1.15 * t + 0.85);
                this.rightEye.scale.setScalar(1.15 * t + 0.85);
            }
            if (this.leftPupil) {
                this.leftPupil.scale.setScalar(1 - 0.15 * t);
                this.rightPupil.scale.setScalar(1 - 0.15 * t);
            }
        }
        // Embarrassed: Eyes slightly averted, droopy
        else if (this.emotionOverride === LunaAvatar.EMOTION_COLORS['embarrassed']) {
            if (this.leftPupil) {
                this.leftPupil.position.x = -0.18 - 0.02 * t;
                this.leftPupil.position.y = 0.12 - 0.01 * t;
                this.rightPupil.position.x = 0.12 - 0.02 * t;
                this.rightPupil.position.y = 0.12 - 0.01 * t;
            }
            if (this.leftEye) {
                this.leftEye.scale.y = 1 - 0.1 * t;
                this.rightEye.scale.y = 1 - 0.1 * t;
            }
        }
    }

    // ── Emotion Particle Burst ───────────────────────────────────

    /**
     * Trigger a burst of particles in the emotion's color.
     * Called when intensity > 0.7 for a visual 'sparkle' effect.
     * 
     * Session 34: Emotion-specific particle shapes and behaviors:
     * - happy/grateful: Star sparkles — spiral outward with twinkling
     * - sad/tired: Rain drops — fall downward with gentle drift
     * - angry/frustrated: Fire sparks — shoot out fast and erratically
     * - curious: Floating orbs — drift upward slowly
     * - excited: Firework burst — explode outward with high energy
     * - default: Radial burst (original behavior)
     */
    triggerEmotionBurst(emotionName) {
        const colors = LunaAvatar.EMOTION_COLORS[emotionName];
        if (!colors) return;

        // Emotion-specific burst configuration
        const burstProfiles = {
            happy:     { count: 16, size: 0.035, speed: 0.025, decay: 0.012, gravity: 0, spiral: true,  spread: 0.04 },
            grateful:  { count: 14, size: 0.035, speed: 0.02,  decay: 0.013, gravity: 0, spiral: true,  spread: 0.03 },
            sad:       { count: 10, size: 0.025, speed: 0.01,  decay: 0.018, gravity: -0.002, spiral: false, spread: 0.015 },
            tired:     { count: 8,  size: 0.02,  speed: 0.008, decay: 0.02,  gravity: -0.0015, spiral: false, spread: 0.01 },
            angry:     { count: 18, size: 0.04,  speed: 0.04,  decay: 0.02,  gravity: 0, spiral: false, spread: 0.06 },
            frustrated:{ count: 15, size: 0.035, speed: 0.035, decay: 0.018, gravity: 0.001, spiral: false, spread: 0.05 },
            curious:   { count: 10, size: 0.03,  speed: 0.012, decay: 0.01,  gravity: 0.001, spiral: true,  spread: 0.02 },
            excited:   { count: 20, size: 0.045, speed: 0.05,  decay: 0.015, gravity: -0.001, spiral: true, spread: 0.07 },
            surprised: { count: 14, size: 0.04,  speed: 0.035, decay: 0.012, gravity: -0.002, spiral: true, spread: 0.05 },
            embarrassed:{ count: 8,  size: 0.025, speed: 0.012, decay: 0.015, gravity: 0.001,  spiral: false, spread: 0.02 },
        };

        const profile = burstProfiles[emotionName] || { count: 12, size: 0.04, speed: 0.025, decay: 0.015, gravity: 0, spiral: false, spread: 0.03 };
        const burstCount = profile.count;

        const geo = new THREE.BufferGeometry();
        const positions = new Float32Array(burstCount * 3);
        const velocities = [];

        for (let i = 0; i < burstCount; i++) {
            const angle = (i / burstCount) * Math.PI * 2;
            // Add randomness to angle for more natural feel
            const jitter = (Math.random() - 0.5) * 0.5;
            const a = angle + jitter;

            positions[i * 3] = 0;
            positions[i * 3 + 1] = 0;
            positions[i * 3 + 2] = 0.65;

            const baseSpeed = profile.speed * (0.8 + Math.random() * 0.4);
            let vx, vy;

            if (profile.spiral) {
                // Spiral: tangential + radial velocity
                const tangentSpeed = baseSpeed * 0.6;
                const radialSpeed = baseSpeed * 0.4;
                vx = Math.cos(a) * radialSpeed - Math.sin(a) * tangentSpeed;
                vy = Math.sin(a) * radialSpeed + Math.cos(a) * tangentSpeed;
            } else {
                // Radial: straight outward
                vx = Math.cos(a) * baseSpeed;
                vy = Math.sin(a) * baseSpeed;
            }

            velocities.push({
                x: vx + (Math.random() - 0.5) * profile.spread * 0.5,
                y: vy + (Math.random() - 0.5) * profile.spread * 0.5,
                z: (Math.random() - 0.5) * 0.02,
                life: 1.0,
                decay: profile.decay * (0.8 + Math.random() * 0.4),
                gravity: profile.gravity,
                angle: a,          // for spiral animation
                spiralSpeed: profile.spiral ? 0.05 + Math.random() * 0.03 : 0,
            });
        }

        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const mat = new THREE.PointsMaterial({
            color: colors.glow,
            size: profile.size,
            transparent: true,
            opacity: 0.9,
            sizeAttenuation: true,
        });

        const burst = new THREE.Points(geo, mat);
        this.scene.add(burst);

        // Animate burst with emotion-specific physics
        const animateBurst = () => {
            const pos = burst.geometry.attributes.position.array;
            let alive = false;
            for (let i = 0; i < burstCount; i++) {
                const v = velocities[i];
                if (v.life <= 0) continue;
                alive = true;
                v.life -= v.decay;

                // Apply gravity (positive = float up, negative = fall down)
                v.y += v.gravity;

                // Spiral motion for happy/curious/excited
                if (v.spiralSpeed) {
                    v.angle += v.spiralSpeed;
                    const spiralForce = 0.001;
                    v.x += Math.cos(v.angle) * spiralForce;
                    v.y += Math.sin(v.angle) * spiralForce;
                }

                pos[i * 3] += v.x;
                pos[i * 3 + 1] += v.y;
                pos[i * 3 + 2] += v.z;

                // Friction
                v.x *= 0.96;
                v.y *= 0.96;
                v.z *= 0.96;
            }
            burst.geometry.attributes.position.needsUpdate = true;
            burst.material.opacity = Math.max(0, velocities[0].life * 0.9);

            if (alive) {
                requestAnimationFrame(animateBurst);
            } else {
                this.scene.remove(burst);
                burst.geometry.dispose();
                burst.material.dispose();
            };
        };
        animateBurst();
    }

    // ── Cursor Eye Tracking (Session 36) ──────────────────────

    /**
     * Set up mouse/touch tracking for eye following.
     * Eyes smoothly follow the cursor position relative to the avatar.
     */
    _setupCursorTracking() {
        // Track mouse movement on the container and parent page
        const trackMouse = (e) => {
            if (!this._eyeTrackingEnabled || !this.container) return;
            const rect = this.container.getBoundingClientRect();
            // Normalize mouse position to -1..1 relative to container center
            const centerX = rect.left + rect.width / 2;
            const centerY = rect.top + rect.height / 2;
            const maxDist = Math.max(rect.width, rect.height);
            this._mouseX = Math.max(-1, Math.min(1, (e.clientX - centerX) / (maxDist * 0.5)));
            this._mouseY = Math.max(-1, Math.min(1, -(e.clientY - centerY) / (maxDist * 0.5)));
        };

        // Listen on document for broader tracking range
        document.addEventListener('mousemove', trackMouse, { passive: true });
        document.addEventListener('touchmove', (e) => {
            if (e.touches.length > 0) {
                trackMouse(e.touches[0]);
            }
        }, { passive: true });

        // Reset on mouse leave (look center)
        document.addEventListener('mouseleave', () => {
            this._mouseX = 0;
            this._mouseY = 0;
        });
    }

    /**
     * Enable or disable cursor eye tracking.
     * When disabled, eyes use the default idle look-around animation.
     */
    setEyeTracking(enabled) {
        this._eyeTrackingEnabled = enabled;
        if (!enabled) {
            this._mouseX = 0;
            this._mouseY = 0;
        }
    }

    // ── TTS Mouth Sync (Session 36) ────────────────────────────

    /**
     * Feed real-time audio amplitude to sync mouth animation.
     * Call this from the audio playback system with amplitude values 0-1.
     *
     * @param {number} amplitude - Audio amplitude (0 = silence, 1 = loud)
     */
    setMouthAmplitude(amplitude) {
        this._mouthSyncActive = true;
        this._mouthSyncTarget = Math.max(0, Math.min(1, amplitude));
    }

    /**
     * Stop TTS mouth sync. Mouth returns to emotion/state-based animation.
     */
    stopMouthSync() {
        this._mouthSyncActive = false;
        this._mouthSyncTarget = 0;
    }

    /**
     * Get the current mouth open amount (0-1) for external visualization.
     */
    getMouthOpen() {
        return this.mouthOpen;
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
