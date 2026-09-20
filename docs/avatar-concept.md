# 🌙 Luna Avatar Concept — Diseño Visual

## Concepto: Silueta Femenina Abstracta

Figura minimalista estilo holograma, con líneas suaves y luminosas sobre fondo oscuro. Sin cara definida pero con *presencia*.

**Inspiración:** Cortana (Halo) + YUI (SAO) versión minimalista

## Elementos visuales

### Silueta
- Figura femenina abstracta hecha con **líneas luminosas**
- Cabello fluido que cae como un velo
- Cuerpo definido por 3 líneas verticales suaves
- Hombros curvos y falda que se desvanece
- Sin rasgos faciales — solo forma y presencia

### Aura lunar
- Brillo plateado que pulsa alrededor de la silueta
- Luna creciente flotando como "marca" de Luna
- Color base: plateado/azul claro (#B4C8FF)

### Partículas
- Polvo estelar flotando alrededor
- Velocidad y densidad varían según el estado
- Efecto de vida sin ser un personaje cartoon

## Estados

| Estado | Descripción | Efectos |
|--------|-------------|---------|
| **Idle** | Esperando, escuchando | Aura suave, partículas lentas |
| **Hablando** | Produciendo voz | Aura pulsa rápido, brillo intenso |
| **Pensando** | Procesando información | Partículas giran más rápido, aura intermitente |
| **Moto** | Modo conducción | Brillo sutil, partículas mínimas, modo discreto |
| **Noche** | Modo nocturno | Casi invisible, solo un tenue resplandor |

## Implementación técnica (futura)

- **Framework:** Three.js + WebGL
- **Formato:** Overlay transparente en Electron
- **Audio reactive:** Cambios visuales sincronizados con TTS/STT
- **Partículas:** Sistema de partículas Three.js (Points o instanced meshes)
- **Shaders:** Glow effect con post-processing (UnrealBloomPass)
- **Transiciones:** GSAP o TWEEN para cambios de estado suaves

## Archivos de referencia

- `luna-avatar-concept.html` — Prototipo CSS/HTML del concepto (en workspace)
- Este documento — Especificación del diseño

## Prioridad

**Fase 4 (Polish)** — Implementar después de que el core de voz y el Electron overlay estén sólidos.

---
*Creado: 6 septiembre 2026*
*Feedback Nicolas: "me gusta la idea hay que mejorar la silueta pero esta bastante bien"*
