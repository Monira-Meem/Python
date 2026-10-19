"""
╔══════════════════════════════════════════════════════════════════╗
║    STELLAR ASSAULT  –  v4.1  ENHANCED REWARD SYSTEM            ║
║    Python + Pygame  |  College Presentation Project              ║
╠══════════════════════════════════════════════════════════════════╣
║  HOW TO RUN:  pip install pygame  →  python space_shooter.py     ║
║  CONTROLS:                                                       ║
║    WASD / Arrow Keys  = Move ship                                ║
║    SPACE              = Shoot                                    ║
║    P                  = Pause / Resume                           ║
║    ESC                = Back to menu                             ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ── fix SDL audio BEFORE pygame import ──────────────────────────
import os
import sys
import json
import array as _array  # Python stdlib array – NOT pygame.array
import pygame, random, math
import numpy as np

# ═══════════════════════════════════════════════════════════════
#  PYGAME INIT  (audio with numpy fix)
# ═══════════════════════════════════════════════════════════════
pygame.init()

# Force quit any existing mixer
pygame.mixer.quit()

# Initialize with mono mode
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    if pygame.mixer.get_init():
        print(f"[AUDIO] Initialized: {pygame.mixer.get_init()}")
        _audio_ok = True
    else:
        _audio_ok = False
        print("[AUDIO] Failed to initialize")
except Exception as e:
    print(f"[AUDIO] Error: {e}")
    _audio_ok = False

info = pygame.display.Info()
SW, SH = info.current_w, info.current_h
SCR = pygame.display.set_mode((SW, SH), pygame.RESIZABLE)
pygame.display.set_caption("STELLAR ASSAULT")
CLK = pygame.time.Clock()
FPS = 60

# ── COLOUR PALETTE ──────────────────────────────────────────────
BG = (3, 5, 20)
C_WHITE = (255, 255, 255)
C_OFFWHITE = (215, 220, 240)
C_CYAN = (0, 215, 255)
C_GOLD = (255, 205, 40)
C_ORANGE = (255, 140, 20)
C_RED = (220, 35, 35)
C_RED_D = (115, 10, 10)
C_GREEN = (45, 220, 95)
C_TEAL = (0, 200, 175)
C_YELLOW = (255, 228, 35)
C_SILVER = (190, 205, 225)
C_LTGREY = (140, 155, 180)
C_GREY = (75, 82, 108)
C_DGREY = (20, 24, 45)
C_PINK = (255, 80, 185)
C_PURPLE = (155, 48, 255)
C_BLUE = (66, 135, 245)

# Game states
S_MENU = "menu"
S_PLAY = "play"
S_PAUSE = "pause"
S_OVER = "over"
S_NAME_INPUT = "name_input"
S_SCOREBOARD = "scoreboard"

# ═══════════════════════════════════════════════════════════════
#  SCOREBOARD
# ═══════════════════════════════════════════════════════════════
SCORES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.json")
MAX_SCORES = 10


class Scoreboard:
    """Persistent top-10 scoreboard stored in scores.json."""

    def __init__(self):
        self.entries = []   # list of {"name": str, "score": int, "wave": int}
        self._load()

    def _load(self):
        try:
            if os.path.exists(SCORES_FILE):
                with open(SCORES_FILE, "r") as f:
                    data = json.load(f)
                self.entries = data.get("scores", [])[:MAX_SCORES]
        except Exception:
            self.entries = []

    def _save(self):
        try:
            with open(SCORES_FILE, "w") as f:
                json.dump({"scores": self.entries}, f, indent=2)
        except Exception:
            pass

    def add(self, name: str, score: int, wave: int) -> int:
        """Insert entry, return rank (1-based) or -1 if not in top 10."""
        name = (name.strip() or "PLAYER")[:12].upper()
        self.entries.append({"name": name, "score": score, "wave": wave})
        self.entries.sort(key=lambda e: e["score"], reverse=True)
        self.entries = self.entries[:MAX_SCORES]
        self._save()
        for i, e in enumerate(self.entries):
            if e["name"] == name and e["score"] == score:
                return i + 1
        return -1

    def is_high_score(self, score: int) -> bool:
        """True if score qualifies for top-10."""
        if len(self.entries) < MAX_SCORES:
            return True
        return score > self.entries[-1]["score"]

    def get_top(self):
        return self.entries[:MAX_SCORES]


# ── WAVE / PROGRESSION THRESHOLDS ───────────────────────────────
PHASE2_SCORE = 150
PHASE3_SCORE = 500

# Boss spawn settings
ENEMIES_PER_BOSS = 15
BOSS_SCORE = 100
BOSS_SCORE_INCREMENT = 150

MAX_ENEMIES = 6


# ═══════════════════════════════════════════════════════════════
#  SOUND SYNTHESIS - FIXED WITH NUMPY FOR STEREO COMPATIBILITY
# ═══════════════════════════════════════════════════════════════
def create_sound(frequency, duration_ms, volume=0.3, waveform='sine'):
    """Create a sound using numpy for proper array shaping."""
    if not _audio_ok:
        return None

    try:
        sample_rate = 22050
        num_samples = int(sample_rate * duration_ms / 1000)

        # Create time array
        t = np.linspace(0, duration_ms / 1000, num_samples)

        # Generate waveform
        if waveform == 'sine':
            samples = np.sin(2 * np.pi * frequency * t)
        elif waveform == 'square':
            samples = np.sign(np.sin(2 * np.pi * frequency * t))
        elif waveform == 'noise':
            samples = np.random.uniform(-1, 1, num_samples)
        elif waveform == 'sweep':
            # Frequency sweep
            freq_sweep = frequency * (1 + t / (duration_ms / 1000))
            samples = np.sin(2 * np.pi * freq_sweep * t)
        else:
            samples = np.zeros(num_samples)

        # Apply envelope (fade out)
        envelope = np.ones(num_samples)
        fade_samples = int(0.05 * sample_rate)
        if num_samples > fade_samples:
            envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)

        samples = samples * envelope * volume

        # Convert to 16-bit integers
        samples = (samples * 32767).astype(np.int16)

        # Check if we need stereo or mono
        if pygame.mixer.get_init() and pygame.mixer.get_init()[2] == 2:
            # Stereo - duplicate channel
            samples = np.column_stack((samples, samples))

        # Create sound
        sound = pygame.sndarray.make_sound(samples)
        return sound

    except Exception as e:
        print(f"[AUDIO] Failed to create sound: {e}")
        return None


class SFX:
    """Sound manager with fallback."""
    _ok = False
    _sounds = {}

    @classmethod
    def init(cls):
        global _audio_ok
        if not _audio_ok:
            print("[SFX] Audio not available")
            return

        try:
            pygame.mixer.set_num_channels(16)

            # Create all sounds
            cls._sounds = {
                "shoot": create_sound(880, 100, 0.25, 'square'),
                "explode": create_sound(150, 400, 0.4, 'noise'),
                "powerup": create_sound(660, 300, 0.3, 'sine'),
                "boss": create_sound(100, 800, 0.5, 'sweep'),
                "hit": create_sound(300, 150, 0.3, 'noise'),
                "gameover": create_sound(200, 1200, 0.4, 'sweep'),
                "eshot": create_sound(440, 80, 0.2, 'square'),
                "levelup": create_sound(523, 600, 0.35, 'sine'),
                "collect": create_sound(880, 150, 0.3, 'sine'),
                "shield": create_sound(392, 250, 0.3, 'square'),
            }

            # Check which sounds loaded
            sound_count = sum(1 for s in cls._sounds.values() if s is not None)
            if sound_count > 0:
                cls._ok = True
                print(f"[SFX] Loaded {sound_count} sounds")
            else:
                print("[SFX] No sounds loaded")

        except Exception as e:
            print(f"[SFX] Error: {e}")

    @classmethod
    def play(cls, name):
        if cls._ok and name in cls._sounds and cls._sounds[name]:
            try:
                cls._sounds[name].play()
            except:
                pass


# Initialize SFX
SFX.init()


# ═══════════════════════════════════════════════════════════════
#  FONT SYSTEM
# ═══════════════════════════════════════════════════════════════
def _font(size, bold=True):
    for name in ("Segoe UI", "Calibri", "Arial", "Liberation Sans", "DejaVu Sans", "FreeSans"):
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f: return f
        except:
            pass
    return pygame.font.Font(None, size)


def _title_font(size):
    for name in ("Bahnschrift", "Impact", "Arial Black", "Franklin Gothic Heavy", "Arial"):
        try:
            f = pygame.font.SysFont(name, size, bold=True)
            if f: return f
        except:
            pass
    return pygame.font.Font(None, size)


def _mono(size):
    for name in ("Consolas", "Courier New", "DejaVu Sans Mono"):
        try:
            f = pygame.font.SysFont(name, size, bold=True)
            if f: return f
        except:
            pass
    return pygame.font.Font(None, size)


FT = {}


def _load_fonts():
    global FT
    FT = {
        "title_xl": _title_font(88),
        "title_lg": _title_font(58),
        "body_lg": _font(30),
        "body_md": _font(24),
        "body_sm": _font(19),
        "body_xs": _font(14, False),
        "hud_score": _mono(26),
        "hud_sm": _mono(15),
        "pow_lbl": _mono(13),
        "wave_big": _title_font(72),
    }


_load_fonts()


# ═══════════════════════════════════════════════════════════════
#  TEXT RENDERING HELPERS
# ═══════════════════════════════════════════════════════════════
def txt(surf, text, font, x, y, col, center=True, shadow=True, shcol=(0, 0, 0)):
    if shadow:
        s = font.render(text, True, shcol)
        ox = (x - s.get_width() // 2 + 2) if center else (x + 2)
        surf.blit(s, (ox, y + 2))
    t = font.render(text, True, col)
    ox = (x - t.get_width() // 2) if center else x
    surf.blit(t, (ox, y))
    return t.get_width()


def outlined_txt(surf, text, font, x, y, col, outline=(0, 0, 0), center=True):
    r = font.render(text, True, outline)
    w = r.get_width()
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        ox = (x - w // 2 + dx) if center else (x + dx)
        surf.blit(r, (ox, y + dy))
    r2 = font.render(text, True, col)
    ox2 = (x - w // 2) if center else x
    surf.blit(r2, (ox2, y))


def pill_btn(surf, label, cx, cy, w=320, h=50, col=C_CYAN):
    rx, ry = cx - w // 2, cy - h // 2
    rad = h // 2
    bg = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(bg, (8, 12, 42, 215), (0, 0, w, h), border_radius=rad)
    surf.blit(bg, (rx, ry))
    pygame.draw.rect(surf, col, (rx, ry, w, h), 2, border_radius=rad)
    txt(surf, label, FT["body_md"], cx, cy - FT["body_md"].get_height() // 2 + 4, C_WHITE, shadow=True)
    return pygame.Rect(rx, ry, w, h)


# ═══════════════════════════════════════════════════════════════
#  BACKGROUND
# ═══════════════════════════════════════════════════════════════
STAR_COLS = [
    (255, 255, 255), (200, 220, 255), (255, 238, 198),
    (180, 195, 255), (255, 205, 205), (198, 255, 215),
]


class Star:
    def __init__(self, y=None):
        self.reset(y if y is not None else random.randint(0, SH))

    def reset(self, y=0):
        self.x = random.uniform(0, SW)
        self.y = float(y)
        self.sp = random.uniform(0.15, 1.9)
        self.r = random.choices([1, 1, 1, 2, 3], [40, 30, 14, 10, 6])[0]
        self.col = random.choice(STAR_COLS)
        self.tw = random.uniform(0, math.pi * 2)
        self.tws = random.uniform(0.012, 0.065)

    def update(self):
        self.y += self.sp
        self.tw += self.tws
        if self.y > SH + 4:
            self.reset()

    def draw(self, s):
        b = 0.55 + 0.45 * abs(math.sin(self.tw))
        c = tuple(int(ch * b) for ch in self.col)
        if self.r <= 1:
            try:
                s.set_at((int(self.x), int(self.y)), c)
            except:
                pass
        elif self.r == 2:
            pygame.draw.circle(s, c, (int(self.x), int(self.y)), 1)
        else:
            px, py = int(self.x), int(self.y)
            pygame.draw.circle(s, c, (px, py), 2)
            dim = tuple(int(ch * b * 0.4) for ch in self.col)
            for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4)):
                try:
                    s.set_at((px + dx, py + dy), dim)
                except:
                    pass


def _build_nebula():
    ns = pygame.Surface((SW, SH), pygame.SRCALPHA)
    for _ in range(24):
        col = random.choice([
            (52, 16, 108, 10), (16, 36, 128, 9), (16, 72, 150, 7), (68, 16, 92, 9)])
        cx = random.randint(0, SW)
        cy = random.randint(0, SH)
        rx = random.randint(60, 250)
        ry = random.randint(40, 150)
        pygame.draw.ellipse(ns, col, (cx - rx, cy - ry, rx * 2, ry * 2))
    return ns


def _build_beam():
    bs = pygame.Surface((SW, SH), pygame.SRCALPHA)
    cx = SW // 2
    for bw, am in [(230, 5), (145, 10), (80, 20), (42, 32), (18, 48)]:
        for y in range(SH):
            vy = max(0.0, 1.0 - abs(y - SH * 0.43) / (SH * 0.60))
            a = int(am * vy)
            if a > 1:
                pygame.draw.rect(bs, (52, 115, 255, a), (cx - bw // 2, y, bw, 1))
    return bs


def _rebuild_bg():
    global STARS, NEBULA_S, BEAM_S
    STARS = [Star(random.randint(0, SH)) for _ in range(185)]
    NEBULA_S = _build_nebula()
    BEAM_S = _build_beam()


_rebuild_bg()


def draw_bg(surf):
    surf.fill(BG)
    surf.blit(NEBULA_S, (0, 0))
    surf.blit(BEAM_S, (0, 0))
    for s in STARS:
        s.draw(surf)


def tick_stars():
    for s in STARS:
        s.update()


# ═══════════════════════════════════════════════════════════════
#  PARTICLES
# ═══════════════════════════════════════════════════════════════
class Debris:
    def __init__(self, x, y):
        a = random.uniform(0, 2 * math.pi)
        sp = random.uniform(1.5, 8.5)
        self.x = x + random.uniform(-14, 14)
        self.y = y + random.uniform(-14, 14)
        self.vx = math.cos(a) * sp
        self.vy = math.sin(a) * sp * .7
        self.life = random.randint(28, 60)
        self.ml = self.life
        self.w = random.randint(4, 14)
        self.h = random.randint(3, 9)
        self.rot = random.uniform(0, 360)
        self.rs = random.uniform(-9, 9)
        self.col = random.choice([(115, 70, 28), (80, 50, 18), (148, 88, 38), (90, 60, 20)])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.13
        self.rot += self.rs
        self.life -= 1

    def draw(self, s):
        a = self.life / self.ml
        if a < .04:
            return
        c = tuple(int(ch * a) for ch in self.col)
        cx, cy = int(self.x), int(self.y)
        hw, hh = self.w // 2, self.h // 2
        pts = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        r = math.radians(self.rot)
        cr, sr = math.cos(r), math.sin(r)
        rp = [(cx + p[0] * cr - p[1] * sr, cy + p[0] * sr + p[1] * cr) for p in pts]
        pygame.draw.polygon(s, c, rp)

    @property
    def alive(self):
        return self.life > 0


class Spark:
    def __init__(self, x, y, col, fast=False):
        a = random.uniform(0, 2 * math.pi)
        sp = random.uniform(3, 10) if fast else random.uniform(1.5, 5)
        self.x, self.y = float(x), float(y)
        self.vx = math.cos(a) * sp
        self.vy = math.sin(a) * sp
        self.life = random.randint(8, 24)
        self.ml = self.life
        self.col = col

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1
        self.life -= 1

    def draw(self, s):
        a = self.life / self.ml
        sz = max(1, int(3 * a))
        c = tuple(min(255, int(ch * a)) for ch in self.col)
        pygame.draw.circle(s, c, (int(self.x), int(self.y)), sz)

    @property
    def alive(self):
        return self.life > 0


class FloatLabel:
    def __init__(self, x, y, text, col, big=False):
        self.x, self.y = float(x), float(y)
        self.text = text
        self.col = col
        self.font = FT["body_md"] if big else FT["hud_sm"]
        self.life = 100
        self.ml = 100

    def update(self):
        self.y -= 1.0
        self.life -= 1

    def draw(self, s):
        a = self.life / self.ml
        c = tuple(int(ch * a) for ch in self.col)
        t = self.font.render(self.text, True, c)
        s.blit(t, (int(self.x) - t.get_width() // 2, int(self.y)))

    @property
    def alive(self):
        return self.life > 0


# ═══════════════════════════════════════════════════════════════
#  BULLETS
# ═══════════════════════════════════════════════════════════════
class PBullet:
    def __init__(self, x, y, vx=0, speed=18):
        self.x, self.y = float(x), float(y)
        self.vx = vx
        self.vy = -speed
        self.alive = True
        self.trail = []

    def update(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 7:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        if self.y < -30 or self.x < -30 or self.x > SW + 30:
            self.alive = False

    def draw(self, s):
        for i, (tx, ty) in enumerate(self.trail):
            a = (i + 1) / max(1, len(self.trail))
            pygame.draw.circle(s, (0, int(155 * a), int(235 * a)),
                               (int(tx), int(ty)), max(1, int(2 * a)))
        x, y = int(self.x), int(self.y)
        pygame.draw.rect(s, (0, 130, 190), (x - 2, y - 14, 4, 18))
        pygame.draw.rect(s, C_CYAN, (x - 1, y - 16, 2, 18))
        pygame.draw.circle(s, C_WHITE, (x, y - 16), 3)
        pygame.draw.circle(s, C_CYAN, (x, y - 16), 5, 1)

    def get_rect(self):
        return pygame.Rect(self.x - 4, self.y - 18, 8, 22)


class EBullet:
    def __init__(self, x, y, vx=0, vy=5):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y > SH + 20 or self.x < -20 or self.x > SW + 20:
            self.alive = False

    def draw(self, s):
        x, y = int(self.x), int(self.y)
        pygame.draw.circle(s, (140, 12, 12), (x, y), 8)
        pygame.draw.circle(s, C_RED, (x, y), 6)
        pygame.draw.circle(s, C_ORANGE, (x, y), 3)
        pygame.draw.circle(s, C_WHITE, (x, y), 1)
        pygame.draw.line(s, (190, 35, 35), (x, y - 6), (x, y - 12), 2)

    def get_rect(self):
        return pygame.Rect(self.x - 7, self.y - 7, 14, 14)


# ═══════════════════════════════════════════════════════════════
#  POWER-UPS & REWARD ORBS
# ═══════════════════════════════════════════════════════════════
class PowerUp:
    DEFS = {
        "life": (C_GREEN, "+HP"),
        "double": (C_CYAN, "2x"),
        "rapid": (C_YELLOW, ">>"),
        "shield": (C_TEAL, "SHD"),
        "speed": (C_PINK, "SPD"),
        "score": (C_GOLD, "+100"),
        "super": (C_PURPLE, "MEGA"),
        "heal": (C_RED, "FULL"),
        "triple": (C_BLUE, "3x"),
    }

    def __init__(self, x, y, kind):
        self.x, self.y = float(x), float(y)
        self.kind = kind
        self.col, self.lbl = self.DEFS[kind]
        self.alive = True
        self.t = 0

    def update(self):
        self.y += 1.5
        self.t += 1
        if self.y > SH + 50:
            self.alive = False

    def draw(self, s):
        pulse = abs(math.sin(self.t * .09)) * 6
        r = int(20 + pulse)
        x, y = int(self.x), int(self.y)
        pygame.draw.circle(s, tuple(c // 4 for c in self.col), (x, y), r + 7)
        pygame.draw.circle(s, C_DGREY, (x, y), r)
        pygame.draw.circle(s, self.col, (x, y), r - 4)
        pygame.draw.circle(s, C_WHITE, (x, y), r, 1)
        t = FT["pow_lbl"].render(self.lbl, True, (0, 0, 0))
        s.blit(t, (x - t.get_width() // 2, y - t.get_height() // 2))

    def get_rect(self):
        return pygame.Rect(self.x - 22, self.y - 22, 44, 44)


class RewardOrb:
    """Separate reward orbs that appear randomly and give specific bonuses"""
    TYPES = {
        "health": {"color": C_GREEN, "symbol": "❤️", "message": "+1 HEART!", "value": 1},
        "speed": {"color": C_PINK, "symbol": "⚡", "message": "SPEED BOOST!", "value": "temp"},
        "bullet": {"color": C_BLUE, "symbol": "🔫", "message": "BULLET POWER!", "value": "temp"},
        "score": {"color": C_GOLD, "symbol": "💰", "message": "+50 SCORE!", "value": 50},
        "shield": {"color": C_TEAL, "symbol": "🛡️", "message": "SHIELD BONUS!", "value": "temp"},
        "rapid": {"color": C_YELLOW, "symbol": "⚙️", "message": "RAPID BONUS!", "value": "temp"},
    }

    def __init__(self, x, y, orb_type):
        self.x, self.y = float(x), float(y)
        self.type = orb_type
        self.info = self.TYPES[orb_type]
        self.alive = True
        self.t = 0

    def update(self):
        self.y += 1.2  # Slightly slower than powerups
        self.t += 1
        if self.y > SH + 50:
            self.alive = False

    def draw(self, s):
        pulse = abs(math.sin(self.t * 0.12)) * 8
        r = int(14 + pulse)
        x, y = int(self.x), int(self.y)

        # Outer glow
        pygame.draw.circle(s, tuple(c // 3 for c in self.info["color"]), (x, y), r + 5)
        # Main orb
        pygame.draw.circle(s, self.info["color"], (x, y), r)
        pygame.draw.circle(s, C_WHITE, (x, y), r - 3, 2)
        # Inner core
        pygame.draw.circle(s, C_WHITE, (x, y), 4)

        # Draw symbol (using simple shapes instead of emoji for better compatibility)
        if self.type == "health":
            pygame.draw.ellipse(s, C_RED, (x - 6, y - 3, 12, 12))
            pygame.draw.ellipse(s, C_RED, (x - 2, y - 6, 12, 12))
            pygame.draw.polygon(s, C_RED, [(x - 6, y), (x + 6, y), (x, y + 9)])
        elif self.type == "speed":
            pygame.draw.polygon(s, C_WHITE, [(x, y - 8), (x + 8, y), (x + 4, y), (x + 4, y + 4),
                                             (x, y + 4), (x - 4, y), (x - 8, y)])
        elif self.type == "bullet":
            pygame.draw.rect(s, C_WHITE, (x - 2, y - 8, 4, 12))
            pygame.draw.polygon(s, C_WHITE, [(x - 7, y - 4), (x - 2, y - 8), (x - 2, y), (x - 7, y + 4)])
            pygame.draw.polygon(s, C_WHITE, [(x + 7, y - 4), (x + 2, y - 8), (x + 2, y), (x + 7, y + 4)])
        elif self.type == "score":
            pygame.draw.circle(s, C_WHITE, (x, y), 6)
            pygame.draw.line(s, C_WHITE, (x, y - 6), (x, y + 6), 2)
            pygame.draw.line(s, C_WHITE, (x - 6, y), (x + 6, y), 2)
        elif self.type == "shield":
            pygame.draw.polygon(s, C_WHITE, [(x, y - 8), (x + 8, y - 3), (x + 5, y + 6),
                                             (x - 5, y + 6), (x - 8, y - 3)])
        elif self.type == "rapid":
            for i in range(3):
                ang = i * 120
                rad = 6
                ex = x + rad * math.cos(math.radians(ang + self.t * 5))
                ey = y + rad * math.sin(math.radians(ang + self.t * 5))
                pygame.draw.circle(s, C_WHITE, (int(ex), int(ey)), 2)

    def get_rect(self):
        return pygame.Rect(self.x - 18, self.y - 18, 36, 36)


# ═══════════════════════════════════════════════════════════════
#  PLAYER JET
# ═══════════════════════════════════════════════════════════════
class Player:
    MAX_HP = 5

    def __init__(self):
        self.reset()

    def reset(self):
        self.x = SW // 2
        self.y = SH - 130
        self.health = self.MAX_HP
        self.score = 0
        self.hi_score = 0
        self.bullets = []
        self.shoot_cd = 0
        self.double_shot = False
        self.rapid_fire = False
        self.bullet_speed = 18
        self.shield = False
        self.invincible = 0
        self.mega_laser = False
        self.triple_shot = False
        self.ptimer = {"double": 0, "rapid": 0, "shield": 0, "speed": 0, "mega": 0, "triple": 0}
        self.alive = True
        self.eng_t = 0
        self.tilt = 0

    def handle_input(self, keys):
        spd = 6.5
        self.tilt = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= spd
            self.tilt = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += spd
            self.tilt = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= spd
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += spd
        self.x = max(44, min(SW - 44, self.x))
        self.y = max(90, min(SH - 55, self.y))
        self.shoot_cd -= 1
        return keys[pygame.K_SPACE] and self.shoot_cd <= 0

    def shoot(self):
        cd = 6 if self.rapid_fire else 12
        self.shoot_cd = cd
        SFX.play("shoot")
        spd = self.bullet_speed

        if self.mega_laser:
            self.bullets.append(PBullet(self.x, self.y - 30, speed=spd + 5))
            self.bullets.append(PBullet(self.x, self.y - 30, speed=spd + 5))
        elif self.triple_shot:
            self.bullets.append(PBullet(self.x - 15, self.y - 25, vx=-1, speed=spd))
            self.bullets.append(PBullet(self.x, self.y - 30, speed=spd + 2))
            self.bullets.append(PBullet(self.x + 15, self.y - 25, vx=1, speed=spd))
        elif self.double_shot:
            self.bullets += [
                PBullet(self.x - 18, self.y - 22, vx=-0.5, speed=spd),
                PBullet(self.x + 18, self.y - 22, vx=0.5, speed=spd),
            ]
        else:
            self.bullets.append(PBullet(self.x, self.y - 30, speed=spd))

    def collect_reward(self, orb_type, floats, px, py):
        """Collect reward orbs for immediate benefits"""
        SFX.play("collect")

        if orb_type == "health":
            if self.health < self.MAX_HP:
                self.health += 1
                floats.append(FloatLabel(px, py - 30, "+1 HEALTH!", C_GREEN, big=True))
            else:
                self.score += 50
                floats.append(FloatLabel(px, py - 30, "HP FULL! +50", C_GOLD, big=True))

        elif orb_type == "speed":
            self.bullet_speed = 28
            self.ptimer["speed"] = 60 * 10  # 10 seconds
            floats.append(FloatLabel(px, py - 30, "SUPER SPEED!", C_PINK, big=True))

        elif orb_type == "bullet":
            # Grant temporary double shot
            if not self.double_shot and not self.triple_shot and not self.mega_laser:
                self.double_shot = True
                self.ptimer["double"] = 60 * 10
                floats.append(FloatLabel(px, py - 30, "DOUBLE SHOT!", C_BLUE, big=True))
            else:
                # Extend existing powerup
                for ptype in ["double", "triple", "mega"]:
                    if self.ptimer[ptype] > 0:
                        self.ptimer[ptype] += 60 * 5
                        floats.append(FloatLabel(px, py - 30, f"{ptype.upper()} EXTENDED!", C_BLUE, big=True))
                        break
                else:
                    self.double_shot = True
                    self.ptimer["double"] = 60 * 10
                    floats.append(FloatLabel(px, py - 30, "DOUBLE SHOT!", C_BLUE, big=True))

        elif orb_type == "score":
            self.score += 50
            floats.append(FloatLabel(px, py - 30, "+50 SCORE!", C_GOLD, big=True))

        elif orb_type == "shield":
            if not self.shield:
                self.shield = True
                self.ptimer["shield"] = 60 * 8
                floats.append(FloatLabel(px, py - 30, "SHIELD ACTIVE!", C_TEAL, big=True))
            else:
                self.ptimer["shield"] += 60 * 5
                floats.append(FloatLabel(px, py - 30, "SHIELD EXTENDED!", C_TEAL, big=True))

        elif orb_type == "rapid":
            if not self.rapid_fire:
                self.rapid_fire = True
                self.ptimer["rapid"] = 60 * 8
                floats.append(FloatLabel(px, py - 30, "RAPID FIRE!", C_YELLOW, big=True))
            else:
                self.ptimer["rapid"] += 60 * 5
                floats.append(FloatLabel(px, py - 30, "RAPID EXTENDED!", C_YELLOW, big=True))

    def collect(self, kind, floats, px, py):
        SFX.play("collect")
        msgs = {
            "life": ("+1 LIFE!", C_GREEN),
            "double": ("DOUBLE SHOT!", C_CYAN),
            "rapid": ("RAPID FIRE!", C_YELLOW),
            "shield": ("SHIELD ON!", C_TEAL),
            "speed": ("SPEED BOOST!", C_PINK),
            "score": ("+100 BONUS!", C_GOLD),
            "super": ("MEGA LASER!", C_PURPLE),
            "heal": ("FULL HEALTH!", C_RED),
            "triple": ("TRIPLE SHOT!", C_BLUE),
        }
        lbl, col = msgs[kind]
        floats.append(FloatLabel(px, py - 30, lbl, col, big=True))

        if kind == "life":
            if self.health < self.MAX_HP:
                self.health += 1
            else:
                self.score += 25
                floats.append(FloatLabel(px, py - 60, "+25 (HP FULL)", C_GOLD))
        elif kind == "heal":
            self.health = self.MAX_HP
        elif kind == "double":
            self.double_shot = True
            self.triple_shot = False
            self.mega_laser = False
            self.ptimer["double"] = 60 * 8
        elif kind == "triple":
            self.triple_shot = True
            self.double_shot = False
            self.mega_laser = False
            self.ptimer["triple"] = 60 * 8
        elif kind == "super":
            self.mega_laser = True
            self.double_shot = False
            self.triple_shot = False
            self.ptimer["mega"] = 60 * 6
        elif kind == "rapid":
            self.rapid_fire = True
            self.ptimer["rapid"] = 60 * 8
        elif kind == "shield":
            self.shield = True
            self.ptimer["shield"] = 60 * 5
            SFX.play("shield")
        elif kind == "speed":
            self.bullet_speed = 28
            self.ptimer["speed"] = 60 * 8
        elif kind == "score":
            self.score += 100

    def _tick_powers(self):
        for k in list(self.ptimer):
            if self.ptimer[k] > 0:
                self.ptimer[k] -= 1
                if self.ptimer[k] == 0:
                    if k == "double":
                        self.double_shot = False
                    if k == "rapid":
                        self.rapid_fire = False
                    if k == "shield":
                        self.shield = False
                    if k == "speed":
                        self.bullet_speed = 18
                    if k == "mega":
                        self.mega_laser = False
                    if k == "triple":
                        self.triple_shot = False

    def take_damage(self):
        if self.invincible > 0 or self.shield:
            return False
        self.health -= 1
        self.invincible = 90
        if self.health <= 0:
            self.health = 0
            self.alive = False
        return True

    def update(self):
        if self.invincible > 0:
            self.invincible -= 1
        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if b.alive]
        self._tick_powers()
        self.eng_t = (self.eng_t + 1) % 20

    def draw(self, surf):
        if self.invincible > 0 and (self.invincible // 5) % 2:
            return
        x, y = int(self.x), int(self.y)
        tl = self.tilt * 6

        fl = 24 + (self.eng_t % 12)
        fc = C_ORANGE if self.eng_t < 10 else C_YELLOW
        pygame.draw.polygon(surf, (255, 90, 0), [(x - 5, y + 24), (x + 5, y + 24), (x, y + 24 + fl + 8)])
        pygame.draw.polygon(surf, fc, [(x - 4, y + 24), (x + 4, y + 24), (x, y + 24 + fl)])
        pygame.draw.polygon(surf, (255, 240, 200), [(x - 2, y + 24), (x + 2, y + 24), (x, y + 24 + fl // 2)])
        for ox in (-20, 20):
            pygame.draw.polygon(surf, (200, 58, 0), [(x + ox - 4, y + 18), (x + ox + 4, y + 18), (x + ox, y + 30)])
            pygame.draw.polygon(surf, C_ORANGE, [(x + ox - 3, y + 18), (x + ox + 3, y + 18), (x + ox, y + 26)])

        body = [(x + tl, y - 40), (x - 8 + tl, y - 22), (x - 12, y + 2), (x - 10, y + 20),
                (x, y + 26), (x + 10, y + 20), (x + 12, y + 2), (x + 8 + tl, y - 22)]
        pygame.draw.polygon(surf, (142, 20, 20), body)
        pygame.draw.polygon(surf, C_RED, body, 2)
        pygame.draw.polygon(surf, (182, 33, 33), [(x + tl, y - 38), (x - 5, y - 5), (x, y + 12), (x + 5, y - 5)])

        lw = [(x - 12, y - 2), (x - 52, y + 18), (x - 58, y + 30), (x - 36, y + 26), (x - 16, y + 18)]
        rw = [(x + 12, y - 2), (x + 52, y + 18), (x + 58, y + 30), (x + 36, y + 26), (x + 16, y + 18)]
        pygame.draw.polygon(surf, C_RED_D, lw)
        pygame.draw.polygon(surf, C_RED, lw, 2)
        pygame.draw.polygon(surf, C_RED_D, rw)
        pygame.draw.polygon(surf, C_RED, rw, 2)
        pygame.draw.line(surf, (162, 20, 20), (x - 16, y + 2), (x - 50, y + 20), 1)
        pygame.draw.line(surf, (162, 20, 20), (x + 16, y + 2), (x + 50, y + 20), 1)

        pygame.draw.polygon(surf, C_RED_D, [(x - 9, y + 18), (x - 32, y + 30), (x - 28, y + 34), (x - 7, y + 24)])
        pygame.draw.polygon(surf, C_RED_D, [(x + 9, y + 18), (x + 32, y + 30), (x + 28, y + 34), (x + 7, y + 24)])

        for ox in (-36, 36):
            pygame.draw.rect(surf, C_RED_D, (x + ox - 3, y + 8, 6, 12))
            pygame.draw.circle(surf, C_ORANGE, (x + ox, y + 8), 4)

        pygame.draw.ellipse(surf, (108, 18, 18), (x - 11 + tl, y - 32, 22, 28))
        pygame.draw.ellipse(surf, C_SILVER, (x - 10 + tl, y - 32, 20, 24))
        pygame.draw.ellipse(surf, (140, 200, 255), (x - 9 + tl, y - 31, 16, 18))
        pygame.draw.ellipse(surf, C_WHITE, (x - 7 + tl, y - 30, 8, 8))

        for ox in (-14, 14):
            pygame.draw.ellipse(surf, (80, 10, 10), (x + ox - 5, y - 4, 10, 16))
            pygame.draw.ellipse(surf, (162, 20, 20), (x + ox - 4, y - 3, 8, 12))

        if self.double_shot:
            for ox in (-18, 18):
                pygame.draw.circle(surf, C_CYAN, (x + ox, y - 24), 5, 1)

        if self.triple_shot:
            for ox in (-22, 0, 22):
                pygame.draw.circle(surf, C_BLUE, (x + ox, y - 26), 4, 1)

        if self.mega_laser:
            pygame.draw.circle(surf, C_PURPLE, (x, y - 28), 8, 2)
            pygame.draw.circle(surf, C_PURPLE, (x, y - 28), 4)

        if self.bullet_speed > 18:
            pygame.draw.circle(surf, C_PINK, (x, y + 5), 6, 1)

        if self.shield:
            r = 52 + int(math.sin(self.eng_t * .3) * 5)
            pygame.draw.circle(surf, C_TEAL, (x, y), r, 2)
            pygame.draw.circle(surf, (0, 210, 180), (x, y), r - 4, 1)

        for b in self.bullets:
            b.draw(surf)

    def get_rect(self):
        return pygame.Rect(self.x - 20, self.y - 32, 40, 54)


# ═══════════════════════════════════════════════════════════════
#  MENU JET
# ═══════════════════════════════════════════════════════════════
def draw_menu_jet(surf, x, y, t):
    bob = int(math.sin(t * .038) * 10)
    y += bob
    fl = 28 + (t % 12)
    fc = C_ORANGE if t % 20 < 10 else C_YELLOW
    pygame.draw.polygon(surf, (255, 80, 0), [(x - 6, y + 30), (x + 6, y + 30), (x, y + 30 + fl + 10)])
    pygame.draw.polygon(surf, fc, [(x - 5, y + 30), (x + 5, y + 30), (x, y + 30 + fl)])
    pygame.draw.polygon(surf, (255, 238, 195), [(x - 2, y + 30), (x + 2, y + 30), (x, y + 30 + fl // 2)])
    for ox in (-24, 24):
        pygame.draw.polygon(surf, C_ORANGE, [(x + ox - 4, y + 20), (x + ox + 4, y + 20), (x + ox, y + 34)])
    body = [(x, y - 48), (x - 10, y - 28), (x - 15, y + 4), (x - 12, y + 24), (x, y + 30), (x + 12, y + 24),
            (x + 15, y + 4), (x + 10, y - 28)]
    pygame.draw.polygon(surf, (145, 20, 20), body)
    pygame.draw.polygon(surf, C_RED, body, 2)
    pygame.draw.polygon(surf, (182, 33, 33), [(x, y - 46), (x - 6, y - 6), (x, y + 14), (x + 6, y - 6)])
    lw = [(x - 15, y - 2), (x - 62, y + 20), (x - 68, y + 34), (x - 42, y + 30), (x - 18, y + 20)]
    rw = [(x + 15, y - 2), (x + 62, y + 20), (x + 68, y + 34), (x + 42, y + 30), (x + 18, y + 20)]
    for wing in (lw, rw):
        pygame.draw.polygon(surf, C_RED_D, wing)
        pygame.draw.polygon(surf, C_RED, wing, 2)
    pygame.draw.polygon(surf, C_RED_D, [(x - 10, y + 22), (x - 36, y + 34), (x - 32, y + 38), (x - 8, y + 28)])
    pygame.draw.polygon(surf, C_RED_D, [(x + 10, y + 22), (x + 36, y + 34), (x + 32, y + 38), (x + 8, y + 28)])
    for ox in (-42, 42):
        pygame.draw.rect(surf, C_RED_D, (x + ox - 4, y + 10, 8, 14))
        pygame.draw.circle(surf, C_ORANGE, (x + ox, y + 10), 5)
    pygame.draw.ellipse(surf, (110, 18, 18), (x - 13, y - 38, 26, 32))
    pygame.draw.ellipse(surf, C_SILVER, (x - 12, y - 38, 24, 28))
    pygame.draw.ellipse(surf, (140, 200, 255), (x - 11, y - 37, 20, 22))
    pygame.draw.ellipse(surf, C_WHITE, (x - 8, y - 36, 9, 9))
    for ox in (-17, 17):
        pygame.draw.ellipse(surf, (80, 10, 10), (x + ox - 6, y - 2, 12, 18))
        pygame.draw.ellipse(surf, (162, 20, 20), (x + ox - 5, y - 1, 10, 14))


# ═══════════════════════════════════════════════════════════════
#  ENEMY BASE CLASS
# ═══════════════════════════════════════════════════════════════
class EnemyBase:
    def __init__(self, x, y, hp, base_spd, score_val, can_shoot):
        self.x, self.y = float(x), float(y)
        self.hp = hp
        self.mhp = hp
        self.base_spd = base_spd
        self.spd = base_spd
        self.score_val = score_val
        self.can_shoot = can_shoot
        self.scd = random.randint(80, 160)
        self.alive = True
        self.bullets = []
        self.t = 0

    def set_speed(self, mult):
        self.spd = self.base_spd * mult

    def update(self, px, py):
        self.y += self.spd
        self.t += 1
        if self.y > SH + 90:
            self.alive = False
        if self.can_shoot:
            self.scd -= 1
            if self.scd <= 0:
                self._fire(px, py)
                self.scd = random.randint(60, 130)
        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if b.alive]

    def _fire(self, px, py):
        dx = px - self.x
        dy = py - self.y
        d = max(1, math.hypot(dx, dy))
        SFX.play("eshot")
        self.bullets.append(EBullet(self.x, self.y + self._hw(), dx / d * 5, dy / d * 5))

    def take_hit(self, particles):
        self.hp -= 1
        SFX.play("hit")
        for _ in range(5):
            particles.append(Spark(self.x, self.y, C_ORANGE))
        if self.hp <= 0:
            self.alive = False
            for _ in range(30):
                particles.append(Debris(self.x, self.y))
            for _ in range(12):
                particles.append(Spark(self.x, self.y, C_ORANGE, True))
            SFX.play("explode")

    def _hpbar(self, s, bw):
        if self.hp == self.mhp:
            return
        bx = int(self.x) - bw // 2
        by = int(self.y) - self._top() - 16
        pygame.draw.rect(s, (65, 0, 0), (bx, by, bw, 6))
        ratio = self.hp / self.mhp
        col = C_GREEN if ratio > .5 else C_ORANGE if ratio > .25 else C_RED
        pygame.draw.rect(s, col, (bx, by, int(bw * ratio), 6))
        pygame.draw.rect(s, C_WHITE, (bx, by, bw, 6), 1)

    def draw_bullets(self, s):
        for b in self.bullets:
            b.draw(s)

    def _top(self):
        return 32

    def _hw(self):
        return 28

    def get_rect(self):
        hw = self._hw()
        return pygame.Rect(self.x - hw, self.y - self._top(), hw * 2, self._top() * 2)


# ═══════════════════════════════════════════════════════════════
#  INTERCEPTOR
# ═══════════════════════════════════════════════════════════════
class Interceptor(EnemyBase):
    def __init__(self, x, y):
        super().__init__(x, y, hp=2, base_spd=1.4, score_val=15, can_shoot=False)

    def _top(self):
        return 24

    def _hw(self):
        return 20

    def draw(self, s):
        x, y = int(self.x), int(self.y)
        self._hpbar(s, 40)
        g = 10 + int(math.sin(self.t * .3) * 3)
        pygame.draw.circle(s, (195, 55, 0), (x, y + 18), g)
        pygame.draw.circle(s, C_ORANGE, (x, y + 18), g - 3)
        body = [(x, y - 22), (x - 16, y + 6), (x - 12, y + 20), (x, y + 24), (x + 12, y + 20), (x + 16, y + 6)]
        pygame.draw.polygon(s, C_RED_D, body)
        pygame.draw.polygon(s, C_RED, body, 2)
        pygame.draw.polygon(s, C_RED, [(x - 16, y + 4), (x - 30, y + 16), (x - 22, y + 20), (x - 12, y + 16)])
        pygame.draw.polygon(s, C_RED, [(x + 16, y + 4), (x + 30, y + 16), (x + 22, y + 20), (x + 12, y + 16)])
        pygame.draw.circle(s, (58, 0, 0), (x, y - 10), 9)
        pygame.draw.circle(s, C_RED, (x, y - 10), 7)
        pygame.draw.circle(s, C_ORANGE, (x, y - 10), 4)
        pygame.draw.circle(s, C_YELLOW, (x, y - 10), 2)
        for d2 in (4, 8, 12):
            pygame.draw.line(s, (162, 18, 18), (x - 9, y + d2), (x + 9, y + d2), 1)
        self.draw_bullets(s)


# ═══════════════════════════════════════════════════════════════
#  DESTROYER
# ═══════════════════════════════════════════════════════════════
class Destroyer(EnemyBase):
    def __init__(self, x, y):
        super().__init__(x, y, hp=5, base_spd=0.82, score_val=30, can_shoot=True)
        self.wo = random.uniform(0, math.pi * 2)

    def _top(self):
        return 42

    def _hw(self):
        return 34

    def update(self, px, py):
        super().update(px, py)
        self.x += math.sin(self.t * .032 + self.wo) * 1.3

    def draw(self, s):
        x, y = int(self.x), int(self.y)
        self._hpbar(s, 68)
        BD = (38, 14, 98)
        BM = (58, 20, 148)
        AC = (118, 58, 252)
        pygame.draw.circle(s, (33, 9, 88), (x, y), 38)
        pygame.draw.circle(s, BD, (x, y), 34)
        pygame.draw.circle(s, BM, (x, y), 30)
        pygame.draw.circle(s, AC, (x, y), 30, 3)
        pygame.draw.rect(s, (118, 48, 238), (x - 34, y - 42, 68, 11), border_radius=4)
        pygame.draw.rect(s, AC, (x - 34, y - 42, 68, 11), 1, border_radius=4)
        for cx2 in (x - 16, x, x + 16):
            pygame.draw.rect(s, BD, (cx2 - 3, y - 56, 6, 16))
            pygame.draw.circle(s, C_CYAN, (cx2, y - 56), 5)
            pygame.draw.circle(s, C_WHITE, (cx2, y - 56), 2)
        for ex in (x - 12, x + 12):
            pygame.draw.ellipse(s, (24, 4, 62), (ex - 10, y - 10, 20, 15))
            pygame.draw.ellipse(s, AC, (ex - 10, y - 10, 20, 15), 1)
            pygame.draw.circle(s, C_CYAN, (ex, y - 3), 6)
            pygame.draw.circle(s, C_WHITE, (ex, y - 3), 3)
        jaw = [(x - 14, y + 8), (x - 18, y + 22), (x, y + 26), (x + 18, y + 22), (x + 14, y + 8)]
        pygame.draw.polygon(s, (28, 7, 78), jaw)
        pygame.draw.polygon(s, AC, jaw, 1)
        for tx2 in range(x - 12, x + 18, 6):
            pygame.draw.rect(s, (172, 172, 192), (tx2, y + 14, 4, 9))
        for ox in (-34, 34):
            pygame.draw.ellipse(s, BD, (x + ox - 11, y - 10, 22, 30))
            pygame.draw.ellipse(s, BM, (x + ox - 11, y - 10, 22, 30), 2)
            g2 = 7 + int(math.sin(self.t * .25) * 2)
            pygame.draw.circle(s, C_CYAN, (x + ox, y + 16), g2)
        for i, ox in enumerate((-40, 40)):
            a = self.t * .04 * (1 if i == 0 else -1)
            tx2 = x + ox + int(math.cos(a) * 6)
            ty2 = y + int(math.sin(a) * 6)
            pygame.draw.circle(s, BD, (tx2, ty2), 8)
            pygame.draw.circle(s, AC, (tx2, ty2), 6)
            pygame.draw.circle(s, C_CYAN, (tx2, ty2), 3)
        self.draw_bullets(s)


# ═══════════════════════════════════════════════════════════════
#  DREADNOUGHT
# ═══════════════════════════════════════════════════════════════
class Dreadnought(EnemyBase):
    def __init__(self, x, y):
        super().__init__(x, y, hp=10, base_spd=0.50, score_val=60, can_shoot=True)

    def _top(self):
        return 54

    def _hw(self):
        return 46

    def draw(self, s):
        x, y = int(self.x), int(self.y)
        self._hpbar(s, 92)
        BD = (9, 78, 63)
        BM = (13, 108, 86)
        AC = (0, 198, 162)
        pygame.draw.circle(s, (7, 63, 50), (x, y), 54)
        pygame.draw.rect(s, (0, 158, 128), (x - 46, y - 56, 92, 14), border_radius=5)
        pygame.draw.rect(s, AC, (x - 46, y - 56, 92, 14), 2, border_radius=5)
        pygame.draw.rect(s, BD, (x - 64, y - 50, 20, 9))
        pygame.draw.rect(s, BD, (x + 44, y - 50, 20, 9))
        body = [(x, y - 44), (x - 40, y - 20), (x - 46, y + 14), (x - 30, y + 48), (x, y + 56), (x + 30, y + 48),
                (x + 46, y + 14), (x + 40, y - 20)]
        pygame.draw.polygon(s, BD, body)
        pygame.draw.polygon(s, AC, body, 3)
        inner = [(x, y - 30), (x - 26, y - 10), (x - 30, y + 12), (x - 20, y + 36), (x, y + 42), (x + 20, y + 36),
                 (x + 30, y + 12), (x + 26, y - 10)]
        pygame.draw.polygon(s, (7, 63, 50), inner)
        pygame.draw.polygon(s, BM, inner, 2)
        pygame.draw.circle(s, (4, 48, 38), (x, y), 22)
        pygame.draw.circle(s, AC, (x, y), 20, 3)
        pygame.draw.circle(s, C_GREEN, (x, y), 13)
        pygame.draw.circle(s, C_YELLOW, (x, y), 7)
        pygame.draw.circle(s, C_WHITE, (x, y), 3)
        for ex2, ey2 in ((x - 18, y - 18), (x + 18, y - 18)):
            pygame.draw.circle(s, BD, (ex2, ey2), 11)
            pygame.draw.circle(s, AC, (ex2, ey2), 9, 2)
            pygame.draw.circle(s, C_GREEN, (ex2, ey2), 5)
        for i in range(8):
            a = math.pi / 4 * i + self.t * .022
            r = 46
            ex3 = x + int(math.cos(a) * r)
            ey3 = y + int(math.sin(a) * r)
            pygame.draw.line(s, AC, (x, y), (ex3, ey3), 2)
            pygame.draw.circle(s, C_GREEN, (ex3, ey3), 6)
            pygame.draw.circle(s, AC, (ex3, ey3), 3)
        for mx2, sd in ((x - 30, -1), (x + 30, 1)):
            pygame.draw.line(s, AC, (mx2, y + 20), (mx2 + sd * 24, y + 40), 4)
            pygame.draw.line(s, AC, (mx2 + sd * 24, y + 40), (mx2 + sd * 16, y + 54), 3)
            pygame.draw.circle(s, C_GREEN, (mx2 + sd * 16, y + 54), 7)
        self.draw_bullets(s)


# ═══════════════════════════════════════════════════════════════
#  BOSS
# ═══════════════════════════════════════════════════════════════
class Boss(EnemyBase):
    MHP = 80
    P2 = 40

    def __init__(self):
        super().__init__(SW // 2, -145, hp=Boss.MHP, base_spd=0, score_val=500, can_shoot=True)
        self.target_y = 150
        self.entered = False
        self.phase = 1
        self.mdir = 1
        self.bcd = 0
        self.scd2 = 0
        self.laser_t = 0
        self.laser_on = False

    def _top(self):
        return 84

    def _hw(self):
        return 86

    def update(self, px, py):
        self.t += 1
        if not self.entered:
            self.y += 3
            if self.y >= self.target_y:
                self.entered = True
            return
        if self.hp <= self.P2 and self.phase == 1:
            self.phase = 2
            SFX.play("boss")

        spd = 2.4 if self.phase == 2 else 1.6
        self.x += spd * self.mdir
        if self.x > SW - 115 or self.x < 115:
            self.mdir *= -1

        self.bcd -= 1
        if self.bcd <= 0:
            self.bcd = 24 if self.phase == 2 else 42
            for a in (-0.32, -0.12, 0, 0.12, 0.32):
                self.bullets.append(EBullet(self.x, self.y + 66, math.sin(a) * 6, math.cos(a) * 7))
        if self.phase == 2:
            self.scd2 -= 1
            if self.scd2 <= 0:
                self.scd2 = 55
                for i in range(14):
                    a = math.pi * i / 13 + math.pi / 2
                    self.bullets.append(EBullet(self.x, self.y, math.cos(a) * 5, math.sin(a) * 5))
            self.laser_t = (self.laser_t + 1) % 40
            self.laser_on = (self.laser_t < 20)

        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if b.alive]

    def draw(self, s):
        x, y = int(self.x), int(self.y)
        ec = C_RED if self.phase == 1 else (255, 80, 80)
        bw = 265

        if self.phase == 2:
            r2 = 98 + int(abs(math.sin(self.t * .08)) * 28)
            pygame.draw.circle(s, (105, 0, 0), (x, y), r2, 5)
        if self.laser_on and self.phase == 2:
            ls = pygame.Surface((12, SH), pygame.SRCALPHA)
            ls.fill((255, 50, 50, 82))
            s.blit(ls, (x - 6, y + 84))
            pygame.draw.rect(s, (255, 152, 152), (x - 2, y + 84, 4, SH))

        pygame.draw.rect(s, (192, 18, 18), (x - 82, y - 82, 164, 20), border_radius=6)
        pygame.draw.rect(s, C_RED, (x - 82, y - 82, 164, 20), 3, border_radius=6)
        pygame.draw.rect(s, C_RED_D, (x - 114, y - 76, 34, 13))
        pygame.draw.rect(s, C_RED_D, (x + 80, y - 76, 34, 13))

        for w2 in ([(x - 48, y - 34), (x - 86, y - 12), (x - 94, y + 24), (x - 64, y + 48), (x - 42, y + 34)],
                   [(x + 48, y - 34), (x + 86, y - 12), (x + 94, y + 24), (x + 64, y + 48), (x + 42, y + 34)]):
            pygame.draw.polygon(s, C_RED_D, w2)
            pygame.draw.polygon(s, ec, w2, 2)

        body = [(x, y - 66), (x - 60, y - 30), (x - 70, y + 26), (x - 46, y + 66), (x, y + 76), (x + 46, y + 66),
                (x + 70, y + 26), (x + 60, y - 30)]
        pygame.draw.polygon(s, C_RED_D, body)
        pygame.draw.polygon(s, ec, body, 4)
        inner = [(x, y - 46), (x - 40, y - 16), (x - 46, y + 20), (x - 30, y + 48), (x, y + 54), (x + 30, y + 48),
                 (x + 46, y + 20), (x + 40, y - 16)]
        pygame.draw.polygon(s, (90, 8, 8), inner)
        pygame.draw.polygon(s, (150, 14, 14), inner, 2)

        for ex2, ey2, er in ((x - 24, y - 22, 15), (x + 24, y - 22, 15), (x, y + 12, 19)):
            pygame.draw.circle(s, (40, 0, 0), (ex2, ey2), er)
            pygame.draw.circle(s, ec, (ex2, ey2), er, 3)
            pygame.draw.circle(s, C_ORANGE, (ex2, ey2), er - 5)
            pygame.draw.circle(s, C_YELLOW, (ex2, ey2), er - 9)
            pygame.draw.circle(s, C_WHITE, (ex2, ey2), 4)

        for i in range(6):
            a = math.pi / 3 * i + self.t * .026
            tx2 = x + int(math.cos(a) * 64)
            ty2 = y + int(math.sin(a) * 64)
            pygame.draw.circle(s, C_RED_D, (tx2, ty2), 12)
            pygame.draw.circle(s, ec, (tx2, ty2), 10, 2)
            pygame.draw.circle(s, C_ORANGE, (tx2, ty2), 5)

        for mx2, sd in ((x - 48, -1), (x + 48, 1)):
            pygame.draw.line(s, C_RED, (mx2, y + 34), (mx2 + sd * 42, y + 62), 5)
            pygame.draw.line(s, C_RED, (mx2 + sd * 42, y + 62), (mx2 + sd * 30, y + 78), 4)
            pygame.draw.circle(s, C_ORANGE, (mx2 + sd * 30, y + 78), 9)

        bx = x - bw // 2
        by = y - 110
        pygame.draw.rect(s, (60, 0, 0), (bx, by, bw, 14))
        pygame.draw.rect(s, ec, (bx, by, int(bw * self.hp / self.MHP), 14))
        pygame.draw.rect(s, C_WHITE, (bx, by, bw, 14), 1)
        ph = " [PHASE 2 - RAGE]" if self.phase == 2 else " [PHASE 1]"
        bt = FT["hud_sm"].render(f"BOSS  {self.hp}/{self.MHP}{ph}", True, ec)
        s.blit(bt, (x - bt.get_width() // 2, by - 20))

        self.draw_bullets(s)


# ═══════════════════════════════════════════════════════════════
#  HUD
# ═══════════════════════════════════════════════════════════════
def draw_hud(surf, player, wave, boss, boss_active, enemies_to_boss, levelup_t, phase_name):
    hh = 54
    bg = pygame.Surface((SW, hh), pygame.SRCALPHA)
    bg.fill((4, 6, 24, 225))
    surf.blit(bg, (0, 0))
    pygame.draw.rect(surf, (25, 50, 150), (0, hh - 2, SW, 2))
    pygame.draw.rect(surf, (55, 100, 220), (0, hh - 1, SW, 1))

    txt(surf, f"SCORE:  {player.score:,}", FT["hud_score"], 14, 8, C_CYAN, center=False)
    txt(surf, f"BEST:  {player.hi_score:,}", FT["hud_sm"], 14, 36, C_LTGREY, center=False)

    txt(surf, "HP", FT["body_sm"], SW - 226, 16, C_WHITE, center=False)
    for i in range(player.MAX_HP):
        hx = SW - 200 + i * 38
        hy = 10
        if i < player.health:
            pygame.draw.ellipse(surf, C_RED, (hx, hy + 2, 16, 14))
            pygame.draw.ellipse(surf, C_RED, (hx + 12, hy + 2, 16, 14))
            pygame.draw.polygon(surf, C_RED, [(hx, hy + 10), (hx + 28, hy + 10), (hx + 14, hy + 24)])
            pygame.draw.ellipse(surf, (255, 100, 100), (hx + 3, hy + 3, 7, 6))
        else:
            pygame.draw.ellipse(surf, C_RED_D, (hx, hy + 2, 16, 14))
            pygame.draw.ellipse(surf, C_RED_D, (hx + 12, hy + 2, 16, 14))
            pygame.draw.polygon(surf, C_RED_D, [(hx, hy + 10), (hx + 28, hy + 10), (hx + 14, hy + 24)])

    wt = FT["hud_sm"].render(f"WAVE {wave}", True, C_GOLD)
    surf.blit(wt, (SW - wt.get_width() - 10, 36))

    badges = []
    if player.double_shot:
        badges.append((C_CYAN, f"2x {player.ptimer['double'] // 60 + 1}s"))
    if player.triple_shot:
        badges.append((C_BLUE, f"3x {player.ptimer['triple'] // 60 + 1}s"))
    if player.mega_laser:
        badges.append((C_PURPLE, f"MEGA {player.ptimer['mega'] // 60 + 1}s"))
    if player.rapid_fire:
        badges.append((C_YELLOW, f"RAPID {player.ptimer['rapid'] // 60 + 1}s"))
    if player.shield:
        badges.append((C_TEAL, f"SHD {player.ptimer['shield'] // 60 + 1}s"))
    if player.bullet_speed > 18:
        badges.append((C_PINK, f"SPD {player.ptimer['speed'] // 60 + 1}s"))

    total_w = len(badges) * 120
    for i, (col, lbl) in enumerate(badges):
        bx = SW // 2 - total_w // 2 + i * 120
        txt(surf, lbl, FT["hud_sm"], bx + 60, 19, col, center=True)

    if not boss_active and not boss:
        info_txt = f"Phase: {phase_name}   |   Boss in {enemies_to_boss} kills"
        txt(surf, info_txt, FT["body_sm"], SW // 2, hh + 5, C_ORANGE)
    elif boss:
        ph = " - PHASE 2 RAGE" if boss.phase == 2 else ""
        txt(surf, f"BOSS BATTLE{ph}", FT["body_sm"], SW // 2, hh + 5, C_RED)

    if levelup_t > 0:
        a = min(1.0, levelup_t / 60)
        c = tuple(int(ch * a) for ch in C_GOLD)
        outlined_txt(surf, f"WAVE {wave}  -  LEVEL UP!", FT["wave_big"], SW // 2, SH // 2 - 55, c, (0, 0, 0))


# ═══════════════════════════════════════════════════════════════
#  SCREEN DRAWS
# ═══════════════════════════════════════════════════════════════
def draw_menu(surf, hi_score, menu_t):
    draw_bg(surf)
    tick_stars()
    outlined_txt(surf, "STELLAR", FT["title_xl"], SW // 2, SH // 2 - 295, C_CYAN, (0, 55, 105))
    outlined_txt(surf, "ASSAULT", FT["title_xl"], SW // 2, SH // 2 - 200, C_ORANGE, (85, 38, 0))
    txt(surf, "2D Space Shooter   |   Python + Pygame", FT["body_sm"], SW // 2, SH // 2 - 122, C_SILVER)
    draw_menu_jet(surf, SW // 2, SH // 2 - 42, menu_t)
    txt(surf, f"HIGH SCORE :  {hi_score:,}", FT["body_lg"], SW // 2, SH // 2 + 60, C_GOLD)
    pill_btn(surf, "PRESS  ENTER  TO  START", SW // 2, SH // 2 + 130, 385, 54, C_CYAN)
    pill_btn(surf, "TAB  -  SCOREBOARD", SW // 2, SH // 2 + 200, 310, 48, C_GOLD)
    pill_btn(surf, "ESC  -  EXIT", SW // 2, SH // 2 + 263, 240, 46, C_GREY)

    # ── Controls panel ──────────────────────────────────────────
    ctrls = [
        ("WASD / ↑↓←→", "Move Ship"),
        ("SPACE",        "Shoot"),
        ("P",            "Pause / Resume"),
        ("ESC",          "Menu"),
    ]
    panel_w, panel_h = 680, 54
    panel_x = SW // 2 - panel_w // 2
    panel_y = SH - 74
    cpanel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(cpanel, (6, 10, 38, 210), (0, 0, panel_w, panel_h), border_radius=14)
    surf.blit(cpanel, (panel_x, panel_y))
    pygame.draw.rect(surf, C_GREY, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=14)

    col_w = panel_w // len(ctrls)
    for i, (key, action) in enumerate(ctrls):
        cx = panel_x + col_w * i + col_w // 2
        # Key badge
        kb_w = FT["body_sm"].size(key)[0] + 18
        kb_h = 24
        kb_x, kb_y = cx - kb_w // 2, panel_y + 6
        pygame.draw.rect(surf, (30, 40, 100), (kb_x, kb_y, kb_w, kb_h), border_radius=6)
        pygame.draw.rect(surf, C_CYAN, (kb_x, kb_y, kb_w, kb_h), 1, border_radius=6)
        txt(surf, key, FT["body_sm"], cx, kb_y + 2, C_CYAN, center=True, shadow=False)
        txt(surf, action, FT["body_xs"], cx, panel_y + 34, C_OFFWHITE, center=True, shadow=False)

        # Divider between columns
        if i > 0:
            pygame.draw.line(surf, (40, 50, 90),
                             (panel_x + col_w * i, panel_y + 8),
                             (panel_x + col_w * i, panel_y + panel_h - 8), 1)


def draw_gameover(surf, score, hi_score, wave):
    draw_bg(surf)
    outlined_txt(surf, "GAME OVER", FT["title_lg"], SW // 2, SH // 2 - 200, C_RED, (80, 0, 0))
    pygame.draw.line(surf, C_RED_D, (SW // 2 - 200, SH // 2 - 130), (SW // 2 + 200, SH // 2 - 130), 1)
    txt(surf, f"SCORE :  {score:,}", FT["body_lg"], SW // 2, SH // 2 - 108, C_CYAN)
    txt(surf, f"BEST  :  {hi_score:,}", FT["body_lg"], SW // 2, SH // 2 - 58, C_GOLD)
    txt(surf, f"WAVE  :  {wave}", FT["body_md"], SW // 2, SH // 2 - 10, C_SILVER)
    pygame.draw.line(surf, C_GREY, (SW // 2 - 200, SH // 2 + 22), (SW // 2 + 200, SH // 2 + 22), 1)
    pill_btn(surf, "ENTER  -  PLAY AGAIN", SW // 2, SH // 2 + 80, 360, 54, C_GREEN)
    pill_btn(surf, "TAB  -  SCOREBOARD", SW // 2, SH // 2 + 150, 310, 48, C_GOLD)
    pill_btn(surf, "ESC  -  MAIN MENU", SW // 2, SH // 2 + 213, 300, 48, C_GREY)


def draw_paused(surf):
    ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 165))
    surf.blit(ov, (0, 0))
    pw, ph2 = 490, 205
    panel = pygame.Surface((pw, ph2), pygame.SRCALPHA)
    pygame.draw.rect(panel, (10, 14, 46, 215), (0, 0, pw, ph2), border_radius=18)
    pygame.draw.rect(panel, (C_YELLOW[0] // 3, C_YELLOW[1] // 3, 0, 255), (0, 0, pw, ph2), 2, border_radius=18)
    surf.blit(panel, (SW // 2 - pw // 2, SH // 2 - ph2 // 2))
    outlined_txt(surf, "PAUSED", FT["title_lg"], SW // 2, SH // 2 - 72, C_YELLOW, (70, 55, 0))
    txt(surf, "P  to resume     |     ESC  for menu", FT["body_md"], SW // 2, SH // 2 + 32, C_OFFWHITE)


def draw_name_input(surf, score, wave, name_buf, cursor_t):
    """Screen shown after game over asking for player name."""
    draw_bg(surf)
    tick_stars()

    outlined_txt(surf, "NEW HIGH SCORE!", FT["title_lg"], SW // 2, SH // 2 - 260, C_GOLD, (80, 55, 0))
    txt(surf, f"SCORE :  {score:,}    |    WAVE : {wave}", FT["body_lg"], SW // 2, SH // 2 - 175, C_CYAN)

    txt(surf, "ENTER YOUR NAME", FT["body_md"], SW // 2, SH // 2 - 110, C_SILVER)

    # Input box
    bw, bh = 480, 64
    bx, by = SW // 2 - bw // 2, SH // 2 - 68
    box_bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
    pygame.draw.rect(box_bg, (8, 14, 52, 230), (0, 0, bw, bh), border_radius=12)
    surf.blit(box_bg, (bx, by))
    pygame.draw.rect(surf, C_CYAN, (bx, by, bw, bh), 2, border_radius=12)

    # Name text with blinking cursor
    display = name_buf + ("|" if (cursor_t // 30) % 2 == 0 else " ")
    txt(surf, display, FT["body_lg"], SW // 2, by + bh // 2 - FT["body_lg"].get_height() // 2 + 4, C_WHITE)

    txt(surf, "12 characters max  •  letters, digits & spaces", FT["body_xs"], SW // 2, SH // 2 + 20, C_LTGREY)

    pill_btn(surf, "ENTER  -  SAVE SCORE", SW // 2, SH // 2 + 95, 380, 52, C_GREEN)
    pill_btn(surf, "ESC  -  SKIP", SW // 2, SH // 2 + 165, 260, 46, C_GREY)


def draw_scoreboard(surf, scoreboard, menu_t, new_rank=-1):
    """Full scoreboard screen."""
    draw_bg(surf)
    tick_stars()

    outlined_txt(surf, "HIGH SCORES", FT["title_lg"], SW // 2, 42, C_GOLD, (80, 55, 0))
    pygame.draw.line(surf, C_GREY, (SW // 2 - 340, 108), (SW // 2 + 340, 108), 1)

    entries = scoreboard.get_top()
    row_h = 46
    start_y = 126

    rank_cols = [C_GOLD, C_SILVER, (195, 115, 55)]  # gold, silver, bronze

    for i, e in enumerate(entries):
        ry = start_y + i * row_h
        is_new = (i + 1 == new_rank)

        # Row highlight for newly added entry
        if is_new:
            hi = pygame.Surface((700, row_h - 4), pygame.SRCALPHA)
            pygame.draw.rect(hi, (255, 215, 0, 28), (0, 0, 700, row_h - 4), border_radius=8)
            surf.blit(hi, (SW // 2 - 350, ry))

        rank_col = rank_cols[i] if i < 3 else C_LTGREY
        name_col = C_GOLD if is_new else (C_WHITE if i < 3 else C_OFFWHITE)

        # Rank medal / number
        rank_lbl = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i + 1:2}."
        txt(surf, rank_lbl, FT["body_md"], SW // 2 - 300, ry + 8, rank_col, center=False, shadow=False)

        # Name
        txt(surf, e["name"], FT["body_md"], SW // 2 - 230, ry + 8, name_col, center=False, shadow=False)

        # Score
        score_str = f"{e['score']:,}"
        txt(surf, score_str, FT["hud_score"], SW // 2 + 80, ry + 8, rank_col, center=False, shadow=False)

        # Wave
        txt(surf, f"Wave {e['wave']}", FT["body_xs"], SW // 2 + 245, ry + 14, C_GREY, center=False, shadow=False)

    if not entries:
        txt(surf, "No scores yet – be the first!", FT["body_md"], SW // 2, SH // 2 - 20, C_LTGREY)

    pygame.draw.line(surf, C_GREY, (SW // 2 - 340, start_y + len(entries) * row_h + 8),
                     (SW // 2 + 340, start_y + len(entries) * row_h + 8), 1)

    pill_btn(surf, "ESC  -  MAIN MENU", SW // 2, SH - 60, 300, 48, C_GREY)


# ═══════════════════════════════════════════════════════════════
#  GAME MANAGER
# ═══════════════════════════════════════════════════════════════
class Game:
    PU_TABLE = {
        1: [("life", 2), ("double", 2), ("rapid", 2), ("speed", 2), ("score", 3), ("heal", 1)],
        2: [("life", 2), ("double", 2), ("rapid", 2), ("shield", 2), ("speed", 2), ("score", 2), ("triple", 1),
            ("heal", 1)],
        3: [("life", 2), ("double", 2), ("rapid", 2), ("shield", 2), ("speed", 2), ("score", 1), ("super", 1),
            ("triple", 1), ("heal", 1)],
    }

    REWARD_TYPES = ["health", "speed", "bullet", "score", "shield", "rapid"]
    REWARD_WEIGHTS = [3, 2, 2, 2, 1, 1]  # Health appears more frequently

    def __init__(self):
        self.state = S_MENU
        self.hi_score = 0
        self.menu_t = 0
        self.scoreboard = Scoreboard()
        # Update hi_score from saved scores
        top = self.scoreboard.get_top()
        if top:
            self.hi_score = top[0]["score"]
        # Name-input state
        self._name_buf = ""
        self._name_cursor_t = 0
        self._pending_score = 0
        self._pending_wave = 0
        self._last_rank = -1
        self._new()

    def _new(self):
        self.player = Player()
        self.player.hi_score = self.hi_score
        self.enemies = []
        self.powerups = []
        self.rewards = []  # New list for reward orbs
        self.particles = []
        self.floats = []
        self.boss = None
        self.wave = 1
        self.boss_killed = 0
        self.boss_active = False
        self.enemies_killed = 0
        self.enemies_for_boss = ENEMIES_PER_BOSS
        self.min_score_for_boss = BOSS_SCORE
        self.levelup_t = 0
        self.sp_cd = 0
        self.reward_cd = 0  # Cooldown for spawning rewards
        self.gtime = 0
        self._phase = 1

    def _phase_name(self):
        return {1: "Interceptors", 2: "Interceptors + Destroyers", 3: "Full Assault"}[self._phase]

    def _speed_mult(self):
        return 1.0 + (self.wave - 1) * 0.15

    def _update_phase(self):
        sc = self.player.score
        if sc >= PHASE3_SCORE:
            self._phase = 3
        elif sc >= PHASE2_SCORE:
            self._phase = 2

    def _spawn(self):
        self.sp_cd -= 1
        if self.sp_cd > 0:
            return
        self.sp_cd = max(40, 80 - self.gtime // 400)

        if len(self.enemies) >= MAX_ENEMIES + 2:
            return

        x = random.randint(60, SW - 60)
        mult = self._speed_mult()

        if self._phase == 1:
            e = Interceptor(x, -45)
        elif self._phase == 2:
            e = Interceptor(x, -45) if random.random() < 0.6 else Destroyer(x, -60)
        else:
            r = random.random()
            if r < 0.35:
                e = Interceptor(x, -45)
            elif r < 0.65:
                e = Destroyer(x, -60)
            else:
                e = Dreadnought(x, -80)

        e.set_speed(mult)
        self.enemies.append(e)

    def _spawn_reward(self):
        """Spawn random reward orbs independent of enemy kills"""
        self.reward_cd -= 1
        if self.reward_cd > 0:
            return

        # Reset cooldown (8-15 seconds)
        self.reward_cd = random.randint(60 * 8, 60 * 15)

        # Don't spawn too many rewards at once
        if len(self.rewards) >= 3:
            return

        # Random position (avoid edges)
        x = random.randint(80, SW - 80)
        y = random.randint(50, SH - 100)

        # Choose random reward type based on weights
        reward_type = random.choices(self.REWARD_TYPES, weights=self.REWARD_WEIGHTS)[0]
        self.rewards.append(RewardOrb(x, y, reward_type))

    def _maybe_boss(self):
        if (not self.boss_active and not self.boss
                and self.enemies_killed >= self.enemies_for_boss
                and self.player.score >= self.min_score_for_boss):
            self.boss_active = True
            self.enemies.clear()
            self.boss = Boss()
            SFX.play("boss")
            self.enemies_killed = 0
            self.enemies_for_boss = ENEMIES_PER_BOSS + self.boss_killed * 2
            self.min_score_for_boss = self.player.score + BOSS_SCORE_INCREMENT

    def _boss_defeated(self):
        self.boss_killed += 1
        self.wave += 1
        self.boss_active = False

        bonus = 500 + self.boss_killed * 200
        self.player.score += bonus

        for _ in range(3):
            kind = random.choices(["heal", "super", "triple", "double", "shield", "rapid"], [2, 1, 2, 3, 2, 2])[0]
            self.powerups.append(PowerUp(SW // 2 + random.randint(-100, 100), SH // 2 + random.randint(-50, 50), kind))

        if self.player.health < Player.MAX_HP:
            self.player.health += 1

        SFX.play("levelup")
        self.levelup_t = 200

        self.floats.append(FloatLabel(SW // 2, SH // 2 - 80, f"BOSS DEFEATED!  +{bonus} BONUS!", C_GOLD, big=True))
        self.floats.append(
            FloatLabel(SW // 2, SH // 2 - 50, f"WAVE {self.wave}  - POWER-UPS DROPPED!", C_PURPLE, big=True))

    def _try_powerup(self, x, y):
        chance = 0.25 + (self._phase - 1) * 0.05
        if random.random() < chance:
            table = self.PU_TABLE[self._phase]
            kinds, weights = zip(*table)
            k = random.choices(kinds, weights)[0]
            self.powerups.append(PowerUp(x, y, k))

    def _collide(self):
        pr = self.player.get_rect()

        for e in self.enemies[:]:
            er = e.get_rect()
            for b in self.player.bullets[:]:
                if er.colliderect(b.get_rect()):
                    b.alive = False
                    e.take_hit(self.particles)
                    if not e.alive:
                        self.player.score += e.score_val
                        self.enemies_killed += 1
                        self.floats.append(FloatLabel(e.x, e.y - 20, f"+{e.score_val}", C_GOLD))
                        self._try_powerup(e.x, e.y)
            for b in e.bullets[:]:
                if pr.colliderect(b.get_rect()):
                    b.alive = False
                    self.player.take_damage()
            if er.colliderect(pr):
                self.player.take_damage()

        self.enemies = [e for e in self.enemies if e.alive]

        if self.boss:
            br = self.boss.get_rect()
            for b in self.player.bullets[:]:
                if br.colliderect(b.get_rect()):
                    b.alive = False
                    self.boss.take_hit(self.particles)
            if not self.boss.alive:
                self.player.score += self.boss.score_val
                for _ in range(130):
                    self.particles.append(Debris(self.boss.x, self.boss.y))
                for _ in range(55):
                    self.particles.append(Spark(self.boss.x, self.boss.y, C_ORANGE, True))
                SFX.play("explode")
                self._boss_defeated()
                self.boss = None
            else:
                for b in self.boss.bullets[:]:
                    if pr.colliderect(b.get_rect()):
                        b.alive = False
                        self.player.take_damage()

        # Collect powerups
        for p in self.powerups[:]:
            if pr.colliderect(p.get_rect()):
                self.player.collect(p.kind, self.floats, p.x, p.y)
                p.alive = False
        self.powerups = [p for p in self.powerups if p.alive]

        # Collect reward orbs
        for r in self.rewards[:]:
            if pr.colliderect(r.get_rect()):
                self.player.collect_reward(r.type, self.floats, r.x, r.y)
                r.alive = False
        self.rewards = [r for r in self.rewards if r.alive]

    def _update(self):
        keys = pygame.key.get_pressed()
        if self.player.handle_input(keys):
            self.player.shoot()
        self.player.update()
        tick_stars()
        self.gtime += 1
        if self.levelup_t > 0:
            self.levelup_t -= 1

        self._update_phase()

        if not self.boss_active:
            self._spawn()
            self._spawn_reward()  # Spawn independent rewards
            self._maybe_boss()

        for e in self.enemies:
            e.update(self.player.x, self.player.y)
        if self.boss:
            self.boss.update(self.player.x, self.player.y)
        for p in self.powerups:
            p.update()
        for r in self.rewards:
            r.update()
        for p in self.particles:
            p.update()
        for f in self.floats:
            f.update()
        self.particles = [p for p in self.particles if p.alive]
        self.floats = [f for f in self.floats if f.alive]

        self._collide()

        if self.player.score > self.hi_score:
            self.hi_score = self.player.score
            self.player.hi_score = self.hi_score

        if not self.player.alive:
            SFX.play("gameover")
            if self.scoreboard.is_high_score(self.player.score):
                self._pending_score = self.player.score
                self._pending_wave = self.wave
                self._name_buf = ""
                self._name_cursor_t = 0
                self.state = S_NAME_INPUT
            else:
                self.state = S_OVER

    def _draw_game(self, surf):
        draw_bg(surf)
        for p in self.powerups:
            p.draw(surf)
        for r in self.rewards:  # Draw reward orbs
            r.draw(surf)
        for e in self.enemies:
            e.draw(surf)
        if self.boss:
            self.boss.draw(surf)
        for p in self.particles:
            p.draw(surf)
        for f in self.floats:
            f.draw(surf)
        self.player.draw(surf)
        enemies_needed = max(0, self.enemies_for_boss - self.enemies_killed)
        draw_hud(surf, self.player, self.wave, self.boss, self.boss_active, enemies_needed, self.levelup_t,
                 self._phase_name())

    def run(self):
        global SCR, SW, SH
        while True:
            CLK.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if ev.type == pygame.VIDEORESIZE:
                    SW, SH = ev.w, ev.h
                    SCR = pygame.display.set_mode((SW, SH), pygame.RESIZABLE)
                    _load_fonts()
                    _rebuild_bg()
                if ev.type == pygame.KEYDOWN:
                    k = ev.key
                    if self.state == S_MENU:
                        if k == pygame.K_RETURN:
                            self._new()
                            self.state = S_PLAY
                        elif k == pygame.K_TAB:
                            self._last_rank = -1
                            self.state = S_SCOREBOARD
                        elif k == pygame.K_ESCAPE:
                            pygame.quit()
                            sys.exit()
                    elif self.state == S_PLAY:
                        if k == pygame.K_p:
                            self.state = S_PAUSE
                        elif k == pygame.K_ESCAPE:
                            self.state = S_MENU
                    elif self.state == S_PAUSE:
                        if k == pygame.K_p:
                            self.state = S_PLAY
                        elif k == pygame.K_ESCAPE:
                            self.state = S_MENU
                    elif self.state == S_OVER:
                        if k == pygame.K_RETURN:
                            self._new()
                            self.state = S_PLAY
                        elif k == pygame.K_TAB:
                            self._last_rank = -1
                            self.state = S_SCOREBOARD
                        elif k == pygame.K_ESCAPE:
                            self.state = S_MENU
                    elif self.state == S_NAME_INPUT:
                        if k == pygame.K_RETURN:
                            # Save score and go to scoreboard
                            self._last_rank = self.scoreboard.add(
                                self._name_buf, self._pending_score, self._pending_wave)
                            if self._pending_score > self.hi_score:
                                self.hi_score = self._pending_score
                            self.state = S_SCOREBOARD
                        elif k == pygame.K_ESCAPE:
                            # Skip saving
                            self.state = S_OVER
                        elif k == pygame.K_BACKSPACE:
                            self._name_buf = self._name_buf[:-1]
                        else:
                            ch = ev.unicode
                            if ch and (ch.isalnum() or ch == " ") and len(self._name_buf) < 12:
                                self._name_buf += ch
                    elif self.state == S_SCOREBOARD:
                        if k in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_TAB):
                            self.state = S_MENU

            self.menu_t += 1

            if self.state == S_MENU:
                draw_menu(SCR, self.hi_score, self.menu_t)
            elif self.state == S_PLAY:
                self._update()
                self._draw_game(SCR)
            elif self.state == S_PAUSE:
                self._draw_game(SCR)
                draw_paused(SCR)
            elif self.state == S_OVER:
                draw_gameover(SCR, self.player.score, self.hi_score, self.wave)
            elif self.state == S_NAME_INPUT:
                self._name_cursor_t += 1
                draw_name_input(SCR, self._pending_score, self._pending_wave,
                                self._name_buf, self._name_cursor_t)
            elif self.state == S_SCOREBOARD:
                draw_scoreboard(SCR, self.scoreboard, self.menu_t, self._last_rank)

            pygame.display.flip()


if __name__ == "__main__":
    Game().run()