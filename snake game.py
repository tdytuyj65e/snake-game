
import pygame
import random
import sys
import math
import os

# ---------------- KONFIGURASI ----------------
LEBAR, TINGGI = 700, 560
UKURAN_SEL = 24
GRID_ATAS = 90
KOLOM = LEBAR // UKURAN_SEL
BARIS = (TINGGI - GRID_ATAS) // UKURAN_SEL

FPS_LAYAR = 60
LANGKAH_AWAL = 8.0
LANGKAH_MAKS = 16.0

HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "high_score.txt")

# ---------------- WARNA ----------------
BG_ATAS = (14, 20, 32)
BG_BAWAH = (26, 34, 51)
HIJAU_TERANG = (110, 231, 150)
HIJAU_UTAMA = (60, 190, 120)
HIJAU_GELAP = (30, 120, 80)
MERAH = (240, 90, 90)
MERAH_GLOW = (255, 140, 120)
KUNING = (250, 210, 90)
PUTIH = (245, 245, 250)
ABU_TERANG = (170, 180, 200)
UNGU = (150, 120, 240)
AKSEN = (100, 220, 255)

pygame.init()

layar = pygame.display.set_mode((LEBAR, TINGGI))
pygame.display.set_caption("Snake — Pygame Edition")
jam = pygame.time.Clock()


def muat_font(ukuran, bold=False):
    nama = "Poppins-Bold.ttf" if bold else "Poppins-Medium.ttf"
    path = f"/usr/share/fonts/truetype/google-fonts/{nama}"
    if os.path.exists(path):
        return pygame.font.Font(path, ukuran)
    return pygame.font.SysFont("arial", ukuran, bold=bold)


FONT_JUDUL = muat_font(64, bold=True)
FONT_BESAR = muat_font(40, bold=True)
FONT_SEDANG = muat_font(26, bold=True)
FONT_KECIL = muat_font(18)
FONT_MINI = muat_font(15)


# ---------------- UTIL ----------------
def baca_highscore():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def simpan_highscore(nilai):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(nilai))
    except Exception:
        pass


def gambar_gradasi_vertikal(surface, atas, bawah, rect=None):
    if rect is None:
        rect = surface.get_rect()
    x, y, w, h = rect
    for i in range(h):
        t = i / max(h - 1, 1)
        warna = tuple(int(atas[c] + (bawah[c] - atas[c]) * t) for c in range(3))
        pygame.draw.line(surface, warna, (x, y + i), (x + w, y + i))


def lerp(a, b, t):
    return a + (b - a) * t


def teks_tengah(surface, teks, font, warna, pos, glow=None):
    if glow:
        bayang = font.render(teks, True, glow)
        r = bayang.get_rect(center=(pos[0] + 2, pos[1] + 2))
        surface.blit(bayang, r)
    render = font.render(teks, True, warna)
    rect = render.get_rect(center=pos)
    surface.blit(render, rect)
    return rect


def rounded_rect(surface, rect, warna, radius=8, warna_tepi=None, tebal_tepi=2):
    pygame.draw.rect(surface, warna, rect, border_radius=radius)
    if warna_tepi:
        pygame.draw.rect(surface, warna_tepi, rect, tebal_tepi, border_radius=radius)


# ---------------- PARTIKEL ----------------
class Partikel:
    def __init__(self, x, y, warna):
        sudut = random.uniform(0, math.tau)
        kecepatan = random.uniform(60, 180)
        self.vx = math.cos(sudut) * kecepatan
        self.vy = math.sin(sudut) * kecepatan
        self.x, self.y = x, y
        self.umur = 0.0
        self.umur_maks = random.uniform(0.35, 0.7)
        self.ukuran = random.uniform(3, 6)
        self.warna = warna

    def perbarui(self, dt):
        self.umur += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.9
        self.vy *= 0.9
        return self.umur < self.umur_maks

    def gambar(self, surface):
        progres = 1 - (self.umur / self.umur_maks)
        ukuran = max(self.ukuran * progres, 0)
        alpha = max(int(255 * progres), 0)
        s = pygame.Surface((int(ukuran * 2 + 2), int(ukuran * 2 + 2)), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.warna, alpha), (ukuran + 1, ukuran + 1), ukuran)
        surface.blit(s, (self.x - ukuran - 1, self.y - ukuran - 1))


# ---------------- GAME ----------------
class Game:
    def __init__(self):
        self.highscore = baca_highscore()
        self.reset()
        self.state = "menu"
        self.waktu_menu = 0.0
        self.shake = 0.0

    def reset(self):
        pusat = (KOLOM // 2, BARIS // 2)
        self.ular = [(pusat[0] - i, pusat[1]) for i in range(3)]
        self.arah = (1, 0)
        self.arah_antri = []
        self.progress = 0.0
        self.kecepatan = LANGKAH_AWAL
        self.makanan = self.posisi_baru_makanan()
        self.skor = 0
        self.partikel = []
        self.pulsa_makanan = 0.0
        self.flash_skor = 0.0

    def posisi_baru_makanan(self):
        while True:
            pos = (random.randint(0, KOLOM - 1), random.randint(0, BARIS - 1))
            if pos not in self.ular:
                return pos

    def input_arah(self, arah_baru):
        arah_terakhir = self.arah_antri[-1] if self.arah_antri else self.arah
        bertentangan = (arah_baru[0] == -arah_terakhir[0] and arah_baru[1] == -arah_terakhir[1])
        if not bertentangan and len(self.arah_antri) < 2:
            self.arah_antri.append(arah_baru)

    def langkah_logika(self):
        if self.arah_antri:
            self.arah = self.arah_antri.pop(0)

        kepala = self.ular[0]
        baru = (kepala[0] + self.arah[0], kepala[1] + self.arah[1])

        if not (0 <= baru[0] < KOLOM and 0 <= baru[1] < BARIS) or baru in self.ular:
            self.state = "over"
            self.shake = 12.0
            if self.skor > self.highscore:
                self.highscore = self.skor
                simpan_highscore(self.highscore)
            return

        self.ular.insert(0, baru)
        if baru == self.makanan:
            self.skor += 10
            self.flash_skor = 0.4
            fx = baru[0] * UKURAN_SEL + UKURAN_SEL / 2
            fy = GRID_ATAS + baru[1] * UKURAN_SEL + UKURAN_SEL / 2
            for _ in range(18):
                self.partikel.append(Partikel(fx, fy, random.choice([MERAH, KUNING, MERAH_GLOW])))
            self.makanan = self.posisi_baru_makanan()
            self.kecepatan = min(self.kecepatan + 0.35, LANGKAH_MAKS)
        else:
            self.ular.pop()

    def perbarui(self, dt):
        if self.state == "menu":
            self.waktu_menu += dt
            return
        if self.state != "main":
            return

        self.pulsa_makanan += dt
        if self.flash_skor > 0:
            self.flash_skor -= dt
        if self.shake > 0:
            self.shake = max(self.shake - dt * 40, 0)

        self.progress += dt * self.kecepatan
        while self.progress >= 1.0:
            self.progress -= 1.0
            self.langkah_logika()
            if self.state != "main":
                self.progress = 0
                break

        self.partikel = [p for p in self.partikel if p.perbarui(dt)]

    def posisi_layar(self, sel):
        return (sel[0] * UKURAN_SEL, GRID_ATAS + sel[1] * UKURAN_SEL)

    def gambar_papan(self, surface):
        area = pygame.Rect(0, GRID_ATAS, LEBAR, BARIS * UKURAN_SEL)
        sub = surface.subsurface(area)
        gambar_gradasi_vertikal(sub, (20, 28, 44), (12, 17, 28), sub.get_rect())

        grid_surface = pygame.Surface((LEBAR, BARIS * UKURAN_SEL), pygame.SRCALPHA)
        for x in range(0, LEBAR, UKURAN_SEL):
            pygame.draw.line(grid_surface, (255, 255, 255, 8), (x, 0), (x, BARIS * UKURAN_SEL))
        for y in range(0, BARIS * UKURAN_SEL, UKURAN_SEL):
            pygame.draw.line(grid_surface, (255, 255, 255, 8), (0, y), (LEBAR, y))
        surface.blit(grid_surface, (0, GRID_ATAS))

        pygame.draw.rect(surface, (80, 90, 110), (0, GRID_ATAS, LEBAR, BARIS * UKURAN_SEL), 2)

    def gambar_makanan(self, surface):
        x, y = self.posisi_layar(self.makanan)
        cx, cy = x + UKURAN_SEL / 2, y + UKURAN_SEL / 2
        denyut = (math.sin(self.pulsa_makanan * 6) + 1) / 2
        radius = UKURAN_SEL / 2 - 2 + denyut * 2

        glow = pygame.Surface((UKURAN_SEL * 3, UKURAN_SEL * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*MERAH_GLOW, 60), (UKURAN_SEL * 1.5, UKURAN_SEL * 1.5), radius + 8)
        surface.blit(glow, (cx - UKURAN_SEL * 1.5, cy - UKURAN_SEL * 1.5))

        pygame.draw.circle(surface, MERAH, (cx, cy), radius)
        pygame.draw.circle(surface, (255, 255, 255), (int(cx - radius * 0.3), int(cy - radius * 0.3)), max(radius * 0.25, 1))
        pygame.draw.line(surface, HIJAU_UTAMA, (cx, cy - radius), (cx + 4, cy - radius - 6), 3)

    def gambar_ular(self, surface):
        n = len(self.ular)
        for i in reversed(range(n)):
            sel = self.ular[i]
            x, y = self.posisi_layar(sel)
            t = 1 - (i / max(n - 1, 1))
            warna = tuple(int(lerp(HIJAU_GELAP[c], HIJAU_TERANG[c], t)) for c in range(3))
            rect = pygame.Rect(x + 1, y + 1, UKURAN_SEL - 2, UKURAN_SEL - 2)

            if i == 0:
                rounded_rect(surface, rect, HIJAU_TERANG, radius=9, warna_tepi=(255, 255, 255), tebal_tepi=2)
                dx, dy = self.arah
                ex1 = x + UKURAN_SEL / 2 + dx * 4 - dy * 6
                ey1 = y + UKURAN_SEL / 2 + dy * 4 + dx * 6
                ex2 = x + UKURAN_SEL / 2 + dx * 4 + dy * 6
                ey2 = y + UKURAN_SEL / 2 + dy * 4 - dx * 6
                for ex, ey in [(ex1, ey1), (ex2, ey2)]:
                    pygame.draw.circle(surface, (20, 20, 30), (int(ex), int(ey)), 3)
            else:
                rounded_rect(surface, rect, warna, radius=7)

    def gambar_partikel(self, surface):
        for p in self.partikel:
            p.gambar(surface)

    def gambar_hud(self, surface):
        hud_rect = pygame.Rect(0, 0, LEBAR, GRID_ATAS)
        gambar_gradasi_vertikal(surface, (18, 24, 38), (14, 20, 32), hud_rect)
        pygame.draw.line(surface, (70, 80, 100), (0, GRID_ATAS), (LEBAR, GRID_ATAS), 2)

        judul = FONT_SEDANG.render("SNAKE", True, HIJAU_TERANG)
        surface.blit(judul, (24, 20))

        warna_skor = KUNING if self.flash_skor > 0 else PUTIH
        skor_txt = FONT_BESAR.render(f"{self.skor}", True, warna_skor)
        surface.blit(skor_txt, (24, GRID_ATAS - skor_txt.get_height() - 8))

        label = FONT_MINI.render("SKOR", True, ABU_TERANG)
        surface.blit(label, (24 + skor_txt.get_width() + 10, GRID_ATAS - skor_txt.get_height() // 2 - 18))

        hs_txt = FONT_KECIL.render(f"TERTINGGI  {max(self.highscore, self.skor)}", True, AKSEN)
        rect_hs = hs_txt.get_rect(topright=(LEBAR - 24, 22))
        surface.blit(hs_txt, rect_hs)

        lvl = int((self.kecepatan - LANGKAH_AWAL) / 0.35) + 1
        lvl_txt = FONT_MINI.render(f"LEVEL {lvl}", True, ABU_TERANG)
        rect_lvl = lvl_txt.get_rect(topright=(LEBAR - 24, 48))
        surface.blit(lvl_txt, rect_lvl)

    def gambar_menu(self, surface):
        gambar_gradasi_vertikal(surface, BG_ATAS, BG_BAWAH)
        t = self.waktu_menu
        for i in range(18):
            fase = i * 0.35
            x = 60 + i * 34
            y = TINGGI * 0.35 + math.sin(t * 1.6 + fase) * 26
            warna = tuple(int(lerp(HIJAU_GELAP[c], HIJAU_TERANG[c], i / 18)) for c in range(3))
            pygame.draw.circle(surface, warna, (x, y), 13 - i * 0.2)

        teks_tengah(surface, "SNAKE", FONT_JUDUL, PUTIH, (LEBAR // 2, TINGGI * 0.45), glow=HIJAU_UTAMA)
        teks_tengah(surface, "Pygame Edition", FONT_KECIL, AKSEN, (LEBAR // 2, TINGGI * 0.45 + 46))

        alpha = (math.sin(t * 3) + 1) / 2
        warna_cta = tuple(int(lerp(ABU_TERANG[c], PUTIH[c], alpha)) for c in range(3))
        teks_tengah(surface, "Tekan SPASI untuk mulai", FONT_SEDANG, warna_cta, (LEBAR // 2, TINGGI * 0.68))

        teks_tengah(surface, "Panah/WASD = gerak    P = jeda    ESC = keluar",
                    FONT_MINI, ABU_TERANG, (LEBAR // 2, TINGGI * 0.78))
        teks_tengah(surface, f"Skor tertinggi: {self.highscore}", FONT_KECIL, KUNING, (LEBAR // 2, TINGGI * 0.85))

    def gambar_pause(self, surface):
        overlay = pygame.Surface((LEBAR, TINGGI), pygame.SRCALPHA)
        overlay.fill((10, 14, 22, 190))
        surface.blit(overlay, (0, 0))
        teks_tengah(surface, "JEDA", FONT_JUDUL, PUTIH, (LEBAR // 2, TINGGI // 2 - 30), glow=UNGU)
        teks_tengah(surface, "Tekan P untuk lanjut", FONT_SEDANG, ABU_TERANG, (LEBAR // 2, TINGGI // 2 + 40))

    def gambar_over(self, surface):
        overlay = pygame.Surface((LEBAR, TINGGI), pygame.SRCALPHA)
        overlay.fill((15, 8, 10, 200))
        surface.blit(overlay, (0, 0))
        teks_tengah(surface, "GAME OVER", FONT_JUDUL, MERAH, (LEBAR // 2, TINGGI // 2 - 70), glow=(90, 20, 20))
        teks_tengah(surface, f"Skor kamu: {self.skor}", FONT_BESAR, PUTIH, (LEBAR // 2, TINGGI // 2 - 5))
        baru_rekor = self.skor >= self.highscore and self.skor > 0
        if baru_rekor:
            teks_tengah(surface, "★ REKOR BARU ★", FONT_SEDANG, KUNING, (LEBAR // 2, TINGGI // 2 + 35))
        teks_tengah(surface, "R = main lagi     ESC = keluar", FONT_KECIL, ABU_TERANG, (LEBAR // 2, TINGGI // 2 + 80))

    def render(self, surface):
        offset = (0, 0)
        if self.shake > 0:
            offset = (random.randint(-int(self.shake), int(self.shake)),
                      random.randint(-int(self.shake), int(self.shake)))

        if self.state == "menu":
            self.gambar_menu(surface)
            return

        dunia = pygame.Surface((LEBAR, TINGGI))
        self.gambar_papan(dunia)
        self.gambar_makanan(dunia)
        self.gambar_ular(dunia)
        self.gambar_partikel(dunia)
        self.gambar_hud(dunia)

        surface.fill((8, 10, 16))
        surface.blit(dunia, offset)

        if self.state == "pause":
            self.gambar_pause(surface)
        elif self.state == "over":
            self.gambar_over(surface)


def main():
    game = Game()
    while True:
        dt = jam.tick(FPS_LAYAR) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if game.state == "menu" and event.key == pygame.K_SPACE:
                    game.reset()
                    game.state = "main"

                elif game.state == "main":
                    if event.key in (pygame.K_UP, pygame.K_w):
                        game.input_arah((0, -1))
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        game.input_arah((0, 1))
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        game.input_arah((-1, 0))
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        game.input_arah((1, 0))
                    elif event.key == pygame.K_p:
                        game.state = "pause"

                elif game.state == "pause" and event.key == pygame.K_p:
                    game.state = "main"

                elif game.state == "over" and event.key == pygame.K_r:
                    game.reset()
                    game.state = "main"

        game.perbarui(dt)
        game.render(layar)
        pygame.display.flip()


if __name__ == "__main__":
    main()
