// Sensor looks as Cesium post-process stages. Add more by appending to STYLES.
import * as Cesium from 'cesium';

const HEADER = `
uniform sampler2D colorTexture;
in vec2 v_textureCoordinates;
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
`;

const STYLES = {
  normal: null,
  nvg: `${HEADER}
    void main() {
      vec2 uv = v_textureCoordinates;
      float l = luma(texture(colorTexture, uv).rgb);
      l = pow(l * 1.55, 0.8);
      float scan = 0.92 + 0.08 * sin(uv.y * 900.0);
      float vig = smoothstep(0.85, 0.35, distance(uv, vec2(0.5)));
      out_FragColor = vec4(vec3(0.18, 1.0, 0.35) * l * scan * vig, 1.0);
    }`,
  flir: `${HEADER}
    vec3 ironbow(float t) {
      return clamp(vec3(1.5 * t, 2.0 * t - 0.6, 3.0 * t - 2.0) + vec3(0.0, 0.0, 0.25 * (1.0 - t)), 0.0, 1.0);
    }
    void main() {
      float l = luma(texture(colorTexture, v_textureCoordinates).rgb);
      out_FragColor = vec4(ironbow(smoothstep(0.05, 0.9, l)), 1.0);
    }`,
  crt: `${HEADER}
    void main() {
      vec2 uv = v_textureCoordinates - 0.5;
      uv *= 1.0 + 0.08 * dot(uv, uv);
      uv += 0.5;
      if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) { out_FragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
      float r = texture(colorTexture, uv + vec2(0.0015, 0.0)).r;
      float g = texture(colorTexture, uv).g;
      float b = texture(colorTexture, uv - vec2(0.0015, 0.0)).b;
      vec3 c = floor(vec3(r, g, b) * 12.0) / 12.0;
      c *= vec3(1.0, 0.72, 0.35) * (0.9 + 0.1 * sin(uv.y * 1200.0));
      out_FragColor = vec4(c, 1.0);
    }`,
  noir: `${HEADER}
    void main() {
      float l = luma(texture(colorTexture, v_textureCoordinates).rgb);
      l = clamp((l - 0.5) * 1.3 + 0.5, 0.0, 1.0);
      float vig = smoothstep(0.9, 0.3, distance(v_textureCoordinates, vec2(0.5)));
      out_FragColor = vec4(mix(vec3(l), vec3(l) * vec3(1.07, 0.98, 0.85), 0.15) * vig, 1.0);
    }`,
};

export const STYLE_IDS = Object.keys(STYLES);

export function createSensorStyles(viewer) {
  let stage = null;
  let current = 'normal';
  return {
    get current() {
      return current;
    },
    set(id) {
      if (!(id in STYLES)) id = 'normal';
      if (stage) {
        viewer.scene.postProcessStages.remove(stage);
        stage = null;
      }
      if (STYLES[id]) {
        stage = viewer.scene.postProcessStages.add(new Cesium.PostProcessStage({ fragmentShader: STYLES[id] }));
      }
      current = id;
      viewer.scene.requestRender();
    },
  };
}
