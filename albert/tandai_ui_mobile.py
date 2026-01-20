# ==============================================================================
# TANDAI GC AUTOMATION - Custom Algorithm
# ==============================================================================
# Algoritma otomatis untuk menandai usaha yang belum GC di MatchaPro
# Login & Mobile emulation based on tandai_ui_mobile.py
# Main workflow: Custom algorithm based on user specification
# ==============================================================================

from playwright.sync_api import sync_playwright
import time
import argparse
import random

# ==============================================================================
# KONFIGURASI
# ==============================================================================

# User Agents untuk emulasi Android high-end
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 16; ONEPLUS 15 Build/SKQ1.211202.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 15; SM-S928B Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/133.0.6943.88 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8a Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.102 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 15; POCO X7 Pro Build/UKQ1.231003.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/133.0.6943.45 Mobile Safari/537.36",
]

# URL Targets
URL_LOGIN = "https://matchapro.web.bps.go.id/login"
URL_DIRGC = "https://matchapro.web.bps.go.id/dirgc"


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def log(msg, prefix="[AUTO]"):
    """Print log dengan prefix"""
    print(f"{prefix} {msg}")


def tunggu_loading(page, timeout_ms=60000):
    """
    Tunggu loading overlay selesai.
    Loading overlay muncul saat data sedang diproses.
    """
    try:
        overlay = page.locator('.blockUI.blockOverlay')
        # Tunggu muncul (mungkin tidak muncul jika data kosong)
        try:
            overlay.wait_for(state='visible', timeout=2000)
            log("⏳ Loading... harap tunggu")
            overlay.wait_for(state='hidden', timeout=timeout_ms)
            log("✅ Loading selesai")
        except:
            # Tidak ada loading, lanjut
            pass
    except Exception as e:
        log(f"⚠️ Error saat tunggu loading: {e}")


def tunggu_modal_hilang(page, modal_selector, timeout_ms=10000):
    """Tunggu modal hilang setelah save"""
    try:
        modal = page.locator(modal_selector)
        modal.wait_for(state='hidden', timeout=timeout_ms)
        return True
    except:
        return False


# ==============================================================================
# BROWSER SETUP (dari tandai_ui_mobile.py)
# ==============================================================================

def setup_browser():
    """
    Setup browser dengan emulasi mobile Android.
    Termasuk stealth settings untuk bypass deteksi automation.
    """
    p = sync_playwright().start()
    
    # Launch dengan opsi stealth
    browser = p.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-default-browser-check"
        ],
        ignore_default_args=["--enable-automation"]
    )
    
    # Pilih random user agent
    selected_ua = random.choice(USER_AGENTS)
    log(f"📱 User Agent: {selected_ua[:50]}...")
    
    # Context dengan mobile emulation
    context = browser.new_context(
        user_agent=selected_ua,
        viewport={"width": 412, "height": 915},
        is_mobile=True,
        has_touch=True,
        extra_http_headers={
            "x-requested-with": "id.go.bps.matchapro",
            "sec-ch-ua": '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"'
        }
    )
    
    page = context.new_page()
    
    # Inject script untuk bypass webdriver detection
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'platform', { get: () => 'Linux armv8l' });
        Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 });
    """)
    
    page.set_default_timeout(60000)
    
    return p, browser, context, page


# ==============================================================================
# LOGIN (dari tandai_ui_mobile.py)
# ==============================================================================

def login(page, username, password, otp_code=None):
    """
    Login ke MatchaPro via SSO.
    """
    log("🔐 === PROSES LOGIN ===")
    
    try:
        page.goto(URL_LOGIN, wait_until='domcontentloaded', timeout=120000)
    except Exception as e:
        log(f"⚠️ Timeout navigasi login (lanjut): {e}")
    
    # Cek tombol SSO
    if page.locator('#login-sso').is_visible():
        log("Klik tombol Login SSO...")
        page.click('#login-sso')
        page.wait_for_load_state('networkidle')
        
        log(f"Mengisi username: {username}")
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        
        log("Klik Submit...")
        page.click('input[type="submit"]')
        page.wait_for_load_state('networkidle')
        
        # Handle OTP jika muncul
        try:
            if page.locator('input[name="otp"]').is_visible(timeout=3000):
                if otp_code:
                    log(f"Mengisi OTP: {otp_code}")
                    page.locator('input[name="otp"]').fill(otp_code)
                else:
                    log("⚠️ OTP DIBUTUHKAN! Silakan isi manual.")
                    input("Tekan Enter setelah OTP diisi...")
        except:
            pass
    
    # Tunggu redirect berhasil
    page.wait_for_url("https://matchapro.web.bps.go.id/**", timeout=60000)
    log("✅ LOGIN BERHASIL!")
    return True


# ==============================================================================
# NAVIGASI KE HALAMAN DIRGC
# ==============================================================================

def navigasi_ke_dirgc(page):
    """
    Pergi ke halaman /dirgc setelah login.
    """
    log("🚀 === NAVIGASI KE /dirgc ===")
    
    page.goto(URL_DIRGC, wait_until='domcontentloaded', timeout=60000)
    tunggu_loading(page)
    
    # Cek apakah blocked (mobile only)
    if "Akses lewat matchapro mobile aja" in page.content():
        log("❌ BLOCKED! Server menolak akses (bukan mobile)")
        return False
    
    log("✅ Berhasil masuk /dirgc")
    return True


# ==============================================================================
# STEP 2: KLIK TAB AKTIF
# ==============================================================================

def klik_tab_aktif(page):
    """
    Klik tombol filter 'Aktif'.
    """
    log("📌 Klik Tab 'Aktif'...")
    
    btn_aktif = page.locator('button.filter-tab[data-filter="aktif"]')
    btn_aktif.click(force=True)
    tunggu_loading(page)
    
    log("✅ Tab Aktif dipilih")


# ==============================================================================
# STEP 3: BUKA PANEL FILTER
# ==============================================================================

def buka_panel_filter(page):
    """
    Buka panel Pencarian & Filter jika belum terbuka.
    """
    log("📂 Membuka Panel Filter...")
    
    toggle_filter = page.locator('#toggle-filter')
    
    # Scroll ke atas dulu untuk memastikan filter visible
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)
    
    # Klik toggle filter (selalu klik untuk pastikan terbuka)
    toggle_filter.scroll_into_view_if_needed()
    time.sleep(0.3)
    toggle_filter.click(force=True)
    time.sleep(1.5)  # Animasi expand
    
    # Verifikasi panel terbuka
    f_latlong_container = page.locator('#select2-f_latlong-container')
    try:
        f_latlong_container.wait_for(state='visible', timeout=3000)
        log("✅ Panel Filter terbuka")
    except:
        # Coba klik lagi
        log("⚠️ Panel belum terbuka, coba lagi...")
        toggle_filter.click(force=True)
        time.sleep(1.5)


# ==============================================================================
# STEP 4 & 5: SET FILTER LAT/LONG = ADA KOORDINAT
# ==============================================================================

def set_filter_latlong(page):
    """
    Pilih filter Lat/Long = 'Ada Koordinat'.
    """
    log("🗺️ Set Filter Lat/Long: Ada Koordinat...")
    
    # Scroll ke dropdown
    select2_container = page.locator('#select2-f_latlong-container')
    select2_container.scroll_into_view_if_needed()
    time.sleep(0.5)
    
    # Retry logic untuk klik dropdown
    for attempt in range(3):
        try:
            select2_container.click(force=True)
            time.sleep(0.5)
            
            # Tunggu search field muncul
            search_field = page.locator('.select2-search__field')
            if search_field.is_visible(timeout=2000):
                break
        except:
            log(f"  ⚠️ Attempt {attempt + 1} gagal, retry...")
            time.sleep(1)
    
    # Isi dan submit
    search_field = page.locator('.select2-search__field')
    if search_field.is_visible(timeout=3000):
        search_field.fill('Ada Koordinat')
        time.sleep(0.5)
        page.keyboard.press('Enter')
        tunggu_loading(page)
        log("✅ Filter Lat/Long diterapkan")
    else:
        log("⚠️ Gagal membuka dropdown Lat/Long")


# ==============================================================================
# STEP 6: SET FILTER STATUS GC = BELUM GC
# ==============================================================================

def set_filter_gc(page):
    """
    Pilih filter Status GC = 'Belum GC'.
    """
    log("🏷️ Set Filter Status GC: Belum GC...")
    
    # Retry logic untuk dropdown yang kadang susah
    for attempt in range(3):
        try:
            select2_container = page.locator('#select2-f_gc-container')
            select2_container.click(force=True)
            
            search_field = page.locator('.select2-search__field')
            if search_field.is_visible(timeout=2000):
                break
        except:
            time.sleep(1)
    
    if search_field.is_visible():
        search_field.fill('Belum GC')
        time.sleep(0.5)
        page.keyboard.press('Enter')
        tunggu_loading(page)
        log("✅ Filter Status GC diterapkan")
    else:
        log("⚠️ Gagal membuka dropdown Status GC")


# ==============================================================================
# HELPER: CEK APAKAH CARD SUDAH GC
# ==============================================================================

def card_sudah_gc(card):
    """
    Cek apakah card memiliki badge 'Sudah GC'.
    Return True jika sudah GC.
    """
    try:
        badge = card.locator('.gc-badge')
        return badge.is_visible()
    except:
        return False


# ==============================================================================
# HELPER: BUKA/EXPAND CARD
# ==============================================================================

def expand_card(page, card):
    """
    Klik header card untuk membuka detail.
    Return True jika berhasil expand (usaha-actions visible).
    """
    header = card.locator('.usaha-card-header')
    
    # Scroll ke view
    card.scroll_into_view_if_needed()
    time.sleep(0.5)
    
    # Klik header untuk expand
    header.click(force=True)
    time.sleep(1)  # Tunggu animasi expand
    
    # Cek apakah actions container sudah visible
    actions = card.locator('.usaha-actions')
    try:
        actions.wait_for(state='visible', timeout=3000)
        log("  📂 Card expanded")
        return True
    except:
        # Mungkin perlu klik lagi
        log("  ⚠️ Card belum expand, coba klik lagi...")
        header.click(force=True)
        time.sleep(1)
        try:
            actions.wait_for(state='visible', timeout=3000)
            log("  📂 Card expanded (retry)")
            return True
        except:
            log("  ❌ Gagal expand card")
            return False


# ==============================================================================
# HELPER: KLIK TOMBOL TANDAI
# ==============================================================================

def klik_tombol_tandai(page, card):
    """
    Klik tombol 'Tandai' di dalam card menggunakan JavaScript.
    Ini lebih presisi karena langsung target element by data-id.
    """
    # Ambil data-id dari card
    card_data_id = card.get_attribute('data-id')
    
    if not card_data_id:
        log("  ⚠️ Card tidak punya data-id!")
        return False
    
    log(f"  🔍 Mencari tombol Tandai dengan data-id...")
    
    # Scroll card ke tengah layar dulu
    card.scroll_into_view_if_needed()
    time.sleep(0.5)
    
    # Gunakan JavaScript untuk klik tombol yang TEPAT
    # Ini bypass masalah overlapping elements
    clicked = page.evaluate('''(dataId) => {
        // Cari tombol dengan class btn-tandai dan data-id yang cocok
        const btn = document.querySelector(`button.btn-tandai[data-id="${dataId}"]`);
        if (btn) {
            // Scroll ke button
            btn.scrollIntoView({ behavior: 'instant', block: 'center' });
            // Klik langsung via JS
            btn.click();
            return true;
        }
        return false;
    }''', card_data_id)
    
    if clicked:
        log("  🖱️ Tombol Tandai diklik (via JS)")
        time.sleep(1)  # Tunggu modal muncul
        return True
    else:
        log("  ❌ Tombol Tandai tidak ditemukan!")
        return False


# ==============================================================================
# HELPER: ISI MODAL DAN SAVE
# ==============================================================================

def proses_modal_tandai(page):
    """
    Isi modal konfirmasi tandai:
    - Pilih 'Ditemukan' di dropdown
    - Klik tombol Save
    """
    # Tunggu modal muncul
    modal = page.locator('#modal-konfirmasi-check')
    modal.wait_for(state='visible', timeout=5000)
    
    # Tunggu dropdown hasil GC
    dropdown = page.locator('#tt_hasil_gc')
    dropdown.wait_for(state='visible', timeout=5000)
    
    # Pilih "1. Ditemukan" (value="1")
    log("  📝 Pilih: 1. Ditemukan")
    page.select_option('#tt_hasil_gc', '1')
    time.sleep(0.5)
    
    # Klik tombol Save
    log("  💾 Klik tombol TANDAI USAHA SUDAH DICEK...")
    save_btn = page.locator('#save-tandai-usaha-btn')
    save_btn.click(force=True)
    
    # Tunggu loading overlay
    tunggu_loading(page)
    
    # Handle SweetAlert2 Success Modal (muncul setelah save berhasil)
    try:
        swal_ok_btn = page.locator('.swal2-confirm')
        if swal_ok_btn.is_visible(timeout=3000):
            log("  ✅ Success! Klik OK...")
            swal_ok_btn.click(force=True)
            time.sleep(0.5)
    except:
        pass
    
    # Tunggu modal konfirmasi hilang (penting!)
    try:
        modal.wait_for(state='hidden', timeout=10000)
        log("  ✅ Modal tertutup")
    except:
        log("  ⚠️ Modal masih terbuka, coba tutup manual")
        try:
            close_btn = page.locator('#modal-konfirmasi-check .btn-close')
            if close_btn.is_visible():
                close_btn.click()
        except:
            pass
    
    # Extra wait untuk pastikan DOM terupdate sepenuhnya
    time.sleep(2)


# ==============================================================================
# HELPER: LOAD MORE
# ==============================================================================

def klik_load_more(page):
    """
    Klik tombol 'Muat Lebih Banyak' jika tersedia.
    Return True jika berhasil klik, False jika tidak ada.
    """
    load_more = page.locator('#load-more-btn')
    
    if load_more.is_visible():
        log("📥 Klik 'Muat Lebih Banyak'...")
        load_more.click(force=True)
        tunggu_loading(page)
        time.sleep(2)
        
        # Scroll ke bawah untuk refresh view
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        return True
    
    return False


# ==============================================================================
# MAIN LOOP: PROSES SEMUA CARD
# ==============================================================================

def proses_semua_card(page, max_items=999999):
    """
    Loop utama untuk memproses semua card yang belum GC.
    
    Algoritma:
    1. Ambil semua card yang visible
    2. Untuk setiap card:
       - Skip jika sudah GC (ada badge)
       - Skip jika sudah diproses sebelumnya
       - Expand card, klik Tandai, isi modal, save
    3. Jika semua card di page sudah GC, klik Load More
    4. Ulangi sampai tidak ada lagi Load More
    """
    log("🔄 === MULAI PROSES CARD ===")
    
    total_sukses = 0
    total_gagal = 0
    processed_ids = set()  # Track ID yang sudah diproses
    
    while total_sukses < max_items:
        # Ambil semua card
        cards = page.locator('.usaha-card').all()
        
        if not cards:
            log("⚠️ Tidak ada card ditemukan")
            break
        
        log(f"📊 Ditemukan {len(cards)} card")
        
        ada_yang_diproses = False
        
        for card in cards:
            try:
                # Ambil data-id untuk tracking
                data_id = card.get_attribute('data-id')
                
                if not data_id:
                    continue
                
                # Skip jika sudah diproses
                if data_id in processed_ids:
                    continue
                
                # Skip jika sudah GC (ada badge)
                if card_sudah_gc(card):
                    processed_ids.add(data_id)  # Tandai sebagai 'sudah'
                    continue
                
                # Ambil nama usaha
                try:
                    nama_usaha = card.locator('.usaha-card-title').text_content().strip()
                    # Bersihkan dari badge text jika ada
                    nama_usaha = nama_usaha.split('\n')[0].strip()
                except:
                    nama_usaha = "Unknown"
                
                log(f"\n▶️ Processing: {nama_usaha}")
                
                # Step: Expand card
                if not expand_card(page, card):
                    log(f"  ❌ Gagal expand card, skip")
                    total_gagal += 1
                    continue
                
                # Step: Klik Tandai
                if not klik_tombol_tandai(page, card):
                    log(f"  ❌ Tombol Tandai tidak ditemukan!")
                    total_gagal += 1
                    # Tidak perlu collapse karena akan refresh
                    continue
                
                # Step: Proses Modal
                try:
                    proses_modal_tandai(page)
                    log(f"  ✅ BERHASIL!")
                    total_sukses += 1
                    processed_ids.add(data_id)
                    ada_yang_diproses = True
                except Exception as e:
                    log(f"  ❌ Error modal: {e}")
                    total_gagal += 1
                    # Tutup modal jika masih terbuka
                    try:
                        close_btn = page.locator('#modal-konfirmasi-check .btn-close')
                        if close_btn.is_visible():
                            close_btn.click()
                    except:
                        pass
                
                # Break untuk refresh list (DOM berubah setelah save)
                break
                
            except Exception as e:
                log(f"  ❌ Error umum: {e}")
                total_gagal += 1
                break
        
        # Jika tidak ada yang diproses, coba Load More
        if not ada_yang_diproses:
            log("📭 Semua card di halaman ini sudah GC")
            
            if not klik_load_more(page):
                log("🏁 Tidak ada lagi data. SELESAI!")
                break
    
    return total_sukses, total_gagal


# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description='Automasi Tandai GC - Custom Algorithm')
    parser.add_argument('username', help='Username SSO (wajib)')
    parser.add_argument('password', help='Password SSO (wajib)')
    parser.add_argument('--otp', help='Kode OTP (optional)', default=None)
    parser.add_argument('--max', type=int, default=999999, help='Max items to process')
    
    args = parser.parse_args()
    
    log("=" * 60)
    log("TANDAI GC AUTOMATION - Custom Algorithm")
    log("=" * 60)
    log(f"Username: {args.username}")
    log(f"Max Items: {args.max}")
    
    # Setup browser
    p, browser, context, page = setup_browser()
    
    try:
        # Step 1: Login
        login(page, args.username, args.password, args.otp)
        
        # Step 1.5: Navigasi ke /dirgc
        if not navigasi_ke_dirgc(page):
            log("❌ Gagal navigasi. Berhenti.")
            return
        
        # Step 2: Klik Tab Aktif
        klik_tab_aktif(page)
        
        # Step 3: Buka Panel Filter
        buka_panel_filter(page)
        
        # Step 4-5: Set Filter Lat/Long = Ada Koordinat
        set_filter_latlong(page)
        
        # Step 6: Set Filter Status GC = Belum GC
        set_filter_gc(page)
        
        # Step 7+: Proses semua card
        sukses, gagal = proses_semua_card(page, args.max)
        
        # Hasil akhir
        log("\n" + "=" * 60)
        log("📊 HASIL AKHIR")
        log("=" * 60)
        log(f"✅ Total Sukses: {sukses}")
        log(f"❌ Total Gagal: {gagal}")
        log("=" * 60)
        
    except Exception as e:
        log(f"❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        log("\n⏳ Browser akan ditutup dalam 10 detik...")
        log("(Tekan Ctrl+C untuk keep browser)")
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            log("Browser tetap terbuka. Tutup manual jika perlu.")
            input("Tekan Enter untuk menutup...")
        
        browser.close()
        p.stop()
        log("👋 Selesai!")


if __name__ == "__main__":
    main()
