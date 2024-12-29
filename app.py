from flask import Flask, render_template, request, jsonify
import hashlib
import multiprocessing as mp
import asyncio
import time
import string
import itertools
import random
import psutil
import os

app = Flask(__name__)

# Global variables
total_attempts = 0  # Total number of attempts made to crack the hash
is_cracking = False  # Flag to indicate if the cracking process is running
current_pool = None  # Current multiprocessing pool
manager = None  # Manager for shared state between processes
process_stats = None  # Dictionary to hold the status of each process

def generate_random_password(length=8):
    """Belirtilen uzunlukta rastgele bir şifre oluşturur.

    Args:
        length (int): Oluşturulacak şifrenin uzunluğu. Varsayılan değer 8.

    Returns:
        str: Rastgele oluşturulmuş şifre.
    """
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def generate_md5(password):
    """Verilen şifre için MD5 hash değeri oluşturur.

    Args:
        password (str|bytes): Hash'lenecek şifre.

    Returns:
        str: Oluşturulan MD5 hash değeri.
    """
    return hashlib.md5(password).hexdigest() if isinstance(password, bytes) else hashlib.md5(password.encode()).hexdigest()

def init_worker(shared_stats):
    """Worker process'leri paylaşılan istatistiklerle başlatır.

    Args:
        shared_stats (dict): Process'ler arasında paylaşılan istatistik sözlüğü.
    """
    global process_stats
    process_stats = shared_stats

def process_chunk(chunk, target_hash, start_attempt, process_id):
    """Şifre kombinasyonlarının bir parçasını işleyerek hedef hash'i bulmaya çalışır.

    Args:
        chunk (list): İşlenecek şifre kombinasyonları listesi.
        target_hash (str): Bulunmaya çalışılan hedef hash değeri.
        start_attempt (int): Bu chunk için başlangıç deneme sayısı.
        process_id (int): İşlem yapan process'in ID'si.

    Returns:
        tuple: (bulunan_şifre, deneme_sayısı) çifti. Şifre bulunamazsa (None, deneme_sayısı).
    """
    global process_stats
    try:
        # İstatistik güncelleme aralığını daha da artıralım
        update_interval = 5000
        
        # Batch size'ı maksimuma çıkaralım
        BATCH_SIZE = 500000
        
        # Hash hesaplama optimizasyonu
        md5_hash = hashlib.md5
        target_hash = target_hash.lower()
        current_batch = []
        
        # Pre-allocate buffer for better memory usage
        current_batch = bytearray(BATCH_SIZE * 32)  # Approximate size
        batch_index = 0
        
        for idx, password in enumerate(chunk):
            current_attempt = start_attempt + idx
            
            if isinstance(password, str):
                password = password.encode()
            
            # Direct hash calculation for speed
            current_hash = md5_hash(password).hexdigest()
            if current_hash == target_hash:
                if process_stats is not None:
                    try:
                        process_stats[process_id] = {
                            'current_password': f"FOUND! Password: {password.decode()}",
                            'attempts': current_attempt,
                            'status': 'found'
                        }
                    except Exception as e:
                        print(f"Error updating final stats: {str(e)}")
                return password, current_attempt
            
            # Minimum istatistik güncelleme
            if process_stats is not None and idx % update_interval == 0:
                try:
                    process_stats[process_id] = {
                        'current_password': password.decode(),
                        'attempts': current_attempt,
                        'status': 'running'
                    }
                except Exception as e:
                    print(f"Error updating stats: {str(e)}")
                
    except Exception as e:
        print(f"Error in process_chunk: {str(e)}")
        raise
    
    return None, start_attempt + len(chunk)

def set_process_priority():
    """Process önceliğini maksimum CPU kullanımı için yükseğe ayarlar.

    Raises:
        Exception: Process önceliği ayarlanamadığında oluşan hata.
    """
    try:
        process = psutil.Process(os.getpid())
        if os.name == 'nt':  # Windows
            process.nice(psutil.HIGH_PRIORITY_CLASS)
        else:  # Unix-based systems
            process.nice(-19)  # Highest priority (-20 is max, but reserved for system)
    except Exception as e:
        print(f"Could not set process priority: {e}")

def calculate_optimal_settings():
    """Sistem kaynaklarına göre optimal ayarları hesaplar.

    Returns:
        tuple: (process_sayısı, chunk_boyutu) çifti.
    """
    cpu_count = mp.cpu_count()
    available_memory = psutil.virtual_memory().available
    total_memory = psutil.virtual_memory().total
    
    # Kullanılabilir RAM'in %85'ini kullanmayı hedefleyelim
    target_memory = int(available_memory * 0.85)
    
    # Her process için minimum 40MB ayıralım (daha fazla process için)
    process_per_memory = int(target_memory / (40 * 1024 * 1024))
    
    if os.name == 'nt':  # Windows
        process_count = min(
            process_per_memory,
            cpu_count * 10,  # CPU başına 10 process
            256
        )
    else:
        process_count = min(
            process_per_memory,
            cpu_count * 14,
            512
        )
    
    # Chunk size'ı çok daha fazla artıralım
    chunk_size = max(2000000, min(5000000, int(10000000 / process_count)))
    
    print(f"\nUltra Agresif Process Ayarları:")
    print(f"Toplam RAM: {total_memory / (1024**3):.2f} GB")
    print(f"Kullanılabilir RAM: {available_memory / (1024**3):.2f} GB")
    print(f"Hedef RAM Kullanımı: {target_memory / (1024**3):.2f} GB")
    print(f"CPU Çekirdek Sayısı: {cpu_count}")
    print(f"Process Sayısı: {process_count}")
    print(f"Process Başına RAM: ~{(target_memory/process_count/1024/1024):.2f} MB")
    print(f"Chunk Size: {chunk_size}")
    print(f"Hedeflenen Şifre/Saniye: ~10,000,000+")
    
    return process_count, chunk_size

async def crack_hash(hash_to_crack, max_length=16, process_multiplier=2):
    """Verilen hash değerini kırmak için brute-force yaklaşımı kullanır.

    Args:
        hash_to_crack (str): Kırılmaya çalışılacak hash değeri.
        max_length (int): Denenecek maksimum şifre uzunluğu. Varsayılan 16.
        process_multiplier (int): Process sayısı çarpanı. Varsayılan 2.

    Returns:
        tuple: (bulunan_şifre, toplam_deneme, bulunan_deneme) üçlüsü.
    """
    characters = string.ascii_lowercase + string.ascii_uppercase + string.digits
    found_password = None
    found_attempt = None
    
    # CPU optimization settings
    process_count, chunk_size = calculate_optimal_settings()
    
    print(f"\nOptimized Process Settings:")
    print(f"Available Memory: {psutil.virtual_memory().available / (1024**3):.2f} GB")
    print(f"CPU Cores: {mp.cpu_count()}")
    print(f"Process Count: {process_count}")
    print(f"Chunk Size: {chunk_size}")
    print(f"Memory per Process: ~{(psutil.virtual_memory().available/process_count/1024/1024):.2f} MB")
    
    min_length = 8
    global total_attempts, is_cracking, current_pool, process_stats
    total_attempts = 0
    is_cracking = True
    
    # Reset process statuses
    if process_stats is not None:
        process_stats.clear()  # Clear process_stats when a new process starts
        for i in range(process_count):
            process_stats[i] = {
                'current_password': '',
                'attempts': 0,
                'status': 'waiting'
            }
            time.sleep(0.01)  # Short delay for each process
    
    def chunk_passwords(length):
        """Generate chunks of passwords of the given length."""
        passwords = []
        for p in itertools.product(characters, repeat=length):
            password = ''.join(p)
            passwords.append(password)
            if len(passwords) >= chunk_size:
                yield passwords
                passwords = []
        if passwords:
            yield passwords

    try:
        with mp.Pool(processes=process_count, initializer=init_worker, initargs=(process_stats,)) as pool:
            current_pool = pool
            
            for length in range(min_length, max_length + 1):
                if not is_cracking:
                    print("\nCracking stopped by user")
                    break
                    
                print(f"Trying passwords of length {length}...")
                
                for chunk in chunk_passwords(length):
                    if not is_cracking:
                        break
                    
                    # Create separate chunks for each process
                    chunk_size_per_process = max(1, len(chunk) // process_count)
                    tasks = []
                    
                    for i in range(process_count):
                        start_idx = i * chunk_size_per_process
                        end_idx = start_idx + chunk_size_per_process if i < process_count - 1 else len(chunk)
                        
                        if start_idx < len(chunk):
                            chunk_part = chunk[start_idx:end_idx]
                            tasks.append((chunk_part, hash_to_crack, total_attempts + start_idx, i))
                    
                    if tasks:
                        # Start each process asynchronously
                        results = []
                        for task in tasks:
                            if not is_cracking:
                                break
                            result = pool.apply_async(process_chunk, args=task)
                            results.append(result)
                        
                        # Wait for results
                        for result in results:
                            if not is_cracking:
                                break
                            try:
                                password, attempt = result.get(timeout=1)  # 1 second timeout
                                if password:
                                    found_password = password
                                    found_attempt = attempt
                                    pool.terminate()
                                    break
                            except mp.TimeoutError:
                                continue
                        
                        total_attempts += sum(len(task[0]) for task in tasks)
                        
                        if found_password:
                            break
                    
                if found_password:
                    break
                    
    except Exception as e:
        print(f"Error in process pool: {str(e)}")
        raise
    finally:
        is_cracking = False
        current_pool = None
        # Mark process statuses as stopped
        if process_stats is not None:
            for pid in process_stats.keys():
                process_stats[pid] = {
                    'current_password': '',
                    'attempts': process_stats[pid]['attempts'],
                    'status': 'stopped'
                }
    
    print(f"\nCompleted with {total_attempts:,} total attempts")
    if found_password:
        print(f"Password found at attempt #{found_attempt:,}")
    return found_password, total_attempts, found_attempt

@app.route('/')
def home():
    """Render the home page."""
    return render_template('index.html')

@app.route('/generate_hash', methods=['POST'])
def generate_hash():
    """Verilen şifre için MD5 hash değeri oluşturur.

    Form Args:
        password (str): Hash'lenecek şifre.
        random (str): Rastgele şifre oluşturma seçeneği ('true' veya 'false').
        length (int): Rastgele şifre uzunluğu.

    Returns:
        json: Hash değeri ve kullanılan şifre.
    """
    password = request.form.get('password')
    is_random = request.form.get('random') == 'true'
    length = int(request.form.get('length', 8))
    
    if is_random:
        password = generate_random_password(length)
    
    hash_value = generate_md5(password)
    return jsonify({
        'hash': hash_value,
        'password': password
    })

@app.route('/crack_hash', methods=['POST'])
def crack_hash_route():
    """Hash kırma işlemini başlatır.

    Form Args:
        hash (str): Kırılacak hash değeri.
        max_length (int): Maksimum şifre uzunluğu.
        process_multiplier (int): Process sayısı çarpanı.

    Returns:
        json: İşlem durumu ve mesaj.

    Raises:
        400: Geçersiz istek durumunda.
    """
    global is_cracking
    
    # Do not start a new process if one is already running
    if is_cracking:
        return jsonify({
            'status': 'error',
            'message': 'A cracking process is already running'
        }), 400
    
    hash_to_crack = request.form.get('hash')
    max_length = int(request.form.get('max_length', 16))
    process_multiplier = int(request.form.get('process_multiplier', 2))
    
    if not hash_to_crack:
        return jsonify({'error': 'No hash provided'}), 400
    
    is_cracking = True
    asyncio.run(crack_hash(hash_to_crack, max_length, process_multiplier))
    
    return jsonify({
        'status': 'success',
        'message': 'Hash cracking process started'
    })

@app.route('/status')
def get_status():
    """Hash kırma işleminin mevcut durumunu döndürür.

    Returns:
        json: İşlem durumu, deneme sayısı ve process bilgileri.
    """
    global total_attempts, process_stats, is_cracking
    
    if process_stats is None:
        return jsonify({
            'status': 'stopped',
            'attempts': 0,
            'processes': {}
        })
    
    return jsonify({
        'status': 'running' if is_cracking else 'stopped',
        'attempts': total_attempts,
        'processes': dict(process_stats)
    })

@app.route('/stop', methods=['POST'])
def stop_cracking():
    """Hash kırma işlemini durdurur.

    Returns:
        json: Durdurma işleminin sonucu.

    Raises:
        500: İşlem durdurulurken hata oluştuğunda.
    """
    try:
        global is_cracking, current_pool
        is_cracking = False
        if current_pool:
            current_pool.terminate()
            current_pool = None
        return jsonify({
            'status': 'stopped',
            'message': 'Process successfully stopped'
        }), 200  
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    # Multiprocessing support for Windows
    mp.freeze_support()
    
    # Set high priority for the main process
    set_process_priority()
    
    # Process havuzu için sistem limitlerini yükselt
    if os.name == 'nt':
        import win32process
        import win32con
        try:
            win32process.SetPriorityClass(win32process.GetCurrentProcess(), win32con.HIGH_PRIORITY_CLASS)
        except:
            print("Could not set process priority class")
    
    manager = mp.Manager()
    process_stats = manager.dict()
    
    # Initialize Flask with optimal thread settings
    app.run(debug=True, use_reloader=False, threaded=True)
else:
    # For testing/import purposes
    pass