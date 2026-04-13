from flask import Flask, request, send_file, render_template_string, jsonify
from datetime import datetime
import json
import uuid
import csv
import os
from database import SessionLocal, ShareToken
from certificate_generator import ReportGenerator

app = Flask(__name__)
report_gen = ReportGenerator()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, 'students.csv')

os.makedirs('share_cache', exist_ok=True)
os.makedirs('templates', exist_ok=True)

CSV_FIELDS = ['id', 'total_tasks', 'avg_score', 'homework_completion', 'grade']

def load_student_from_dataset(student_id):
    try:
        if not os.path.exists(DATASET_PATH):
            return None
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row['id']) == student_id:
                    return {
                        'id': int(row['id']),
                        'total_tasks': int(row.get('total_tasks', 0)),
                        'avg_score': int(row.get('avg_score', 0)),
                        'homework_completion': int(row.get('homework_completion', 0)),
                        'grade': int(row.get('grade', 5))
                    }
        return None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def get_all_students_list():
    try:
        if not os.path.exists(DATASET_PATH):
            return []
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return [{'id': int(row['id'])} for row in reader]
    except:
        return []

def get_next_student_id():
    students = get_all_students_list()
    if not students:
        return 1
    return max([s['id'] for s in students]) + 1

def determine_age_group(grade):
    if grade <= 4:
        return 'primary'
    else:
        return 'senior'

@app.route('/api/students', methods=['GET'])
def get_students():
    students = get_all_students_list()
    return jsonify({'status': 'success', 'count': len(students), 'students': students})

@app.route('/api/student/<int:student_id>', methods=['GET'])
def get_student(student_id):
    student = load_student_from_dataset(student_id)
    if not student:
        return jsonify({'error': 'Ученик не найден'}), 404
    return jsonify({'status': 'success', 'student': student})

@app.route('/api/students/add', methods=['POST'])
def add_student():
    try:
        data = request.json
        
        if not data.get('id'):
            return jsonify({'error': 'Не передан ID ученика'}), 400
        
        student_id = data['id']
        grade = data.get('grade', 5)
        
        existing = load_student_from_dataset(student_id)
        if existing:
            return jsonify({'error': f'Ученик с ID {student_id} уже существует'}), 400
        
        new_student = {
            'id': student_id,
            'total_tasks': data.get('total_tasks', 0),
            'avg_score': data.get('avg_score', 0),
            'homework_completion': data.get('homework_completion', 0),
            'grade': grade
        }
        
        file_exists = os.path.exists(DATASET_PATH) and os.path.getsize(DATASET_PATH) > 0
        with open(DATASET_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(new_student)
        
        return jsonify({'status': 'success', 'message': f'Ученик ID {student_id} добавлен'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/students/update/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    try:
        data = request.json
        rows = []
        found = False
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        valid_keys = set(CSV_FIELDS)
        for key in data.keys():
            if key not in valid_keys:
                return jsonify({'error': f'Поле "{key}" не существует в датасете. Допустимые поля: {", ".join(CSV_FIELDS)}'}), 400
        
        for row in rows:
            if int(row['id']) == student_id:
                found = True
                for key, value in data.items():
                    if key in row:
                        row[key] = value
                break
        
        if not found:
            return jsonify({'error': 'Ученик не найден'}), 404
        
        with open(DATASET_PATH, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        
        return jsonify({'status': 'success', 'message': f'Ученик ID {student_id} обновлён'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/students/upload-csv', methods=['POST'])
def upload_csv():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Поддерживаются только CSV файлы'}), 400
        
        file.save(DATASET_PATH)
        
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            if set(reader.fieldnames) != set(CSV_FIELDS):
                return jsonify({'error': f'Неверная структура CSV. Ожидаются колонки: {", ".join(CSV_FIELDS)}'}), 400
            
            rows = list(reader)
            if len(rows) == 0:
                return jsonify({'error': 'CSV файл пуст'}), 400
            
            count = len(rows)
        
        return jsonify({'status': 'success', 'message': f'Загружено {count} учеников', 'count': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/share/generate', methods=['POST'])
def generate_share_token():
    try:
        data = request.json
        if not data.get('id'):
            return jsonify({'error': 'Не передан ID ученика'}), 400
        
        student_id = data['id']
        
        student_data = load_student_from_dataset(student_id)
        if not student_data:
            return jsonify({'error': 'Ученик не найден'}), 404
        
        grade = student_data.get('grade', 5)
        
        student_info = {
            'id': student_id,
            'grade': grade,
            'total_tasks': student_data['total_tasks'],
            'avg_score': student_data['avg_score'],
            'homework_completion': student_data['homework_completion']
        }
        
        share_token = str(uuid.uuid4())
        
        db = SessionLocal()
        new_token = ShareToken(
            token=share_token,
            student_name=f"Ученик {student_id}",
            course_name="Курс",
            student_data_json=json.dumps(student_info, ensure_ascii=False),
            period_type="year",
            period_number=None,
            period_year=datetime.now().year,
            age_group=determine_age_group(grade),
            grade=grade,
            is_active=True
        )
        db.add(new_token)
        db.commit()
        db.close()
        
        share_link = f"{request.host_url}share/{share_token}"
        return jsonify({'status': 'success', 'share_link': share_link})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/share/<token>')
def view_shared_certificate(token):
    db = SessionLocal()
    try:
        share_record = db.query(ShareToken).filter(ShareToken.token == token).first()
        if not share_record:
            return "Ссылка не найдена", 404
        if not share_record.is_active:
            return "Ссылка отозвана", 403
        
        student_data = json.loads(share_record.student_data_json)
        student_data['student_name'] = share_record.student_name
        student_data['grade'] = share_record.grade
        
        period_name = f"{share_record.period_year} учебный год"
        
        png_path, pdf_path = report_gen.generate_report(student_data, share_record.age_group, period_name)
        report_gen.cache_paths[token] = (png_path, pdf_path)
        
        pdf_url = f"/api/download-pdf/{token}"
        png_filename = os.path.basename(png_path)
        
        return render_template_string(f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Твой отчёт — {share_record.student_name}</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    background: #0F172A;
                    display: flex;
                    justify-content: center;
                    padding: 40px 20px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }}
                .container {{ max-width: 900px; width: 100%; }}
                .report-image {{
                    width: 100%;
                    border-radius: 24px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.4);
                    margin-bottom: 30px;
                }}
                .btn-group {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    justify-content: center;
                    background: #1E293B;
                    padding: 24px;
                    border-radius: 24px;
                    margin-bottom: 20px;
                }}
                button {{
                    padding: 12px 24px;
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                    border-radius: 40px;
                    cursor: pointer;
                    transition: 0.3s;
                }}
                button:hover {{ transform: translateY(-2px); }}
                .btn-png {{ background: #10B981; color: white; }}
                .btn-pdf {{ background: #DC2626; color: white; }}
                .btn-vk {{ background: #0077FF; color: white; }}
                .btn-telegram {{ background: #0088cc; color: white; }}
                .btn-whatsapp {{ background: #25D366; color: white; }}
                .btn-email {{ background: #EA4335; color: white; }}
                .btn-copy {{ background: #6B7280; color: white; }}
                .share-link-box {{
                    background: #1E293B;
                    border-radius: 16px;
                    padding: 16px;
                    display: flex;
                    gap: 12px;
                }}
                .share-link-box input {{
                    flex: 1;
                    padding: 12px;
                    background: #0F172A;
                    border: 1px solid #334155;
                    border-radius: 12px;
                    color: white;
                }}
                .success-message {{
                    background: #10B981;
                    color: white;
                    padding: 12px;
                    border-radius: 12px;
                    margin-top: 16px;
                    text-align: center;
                    display: none;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <img src="/static/reports/{png_filename}" class="report-image" alt="Отчёт">
                <div class="btn-group">
                    <button class="btn-png" onclick="downloadPNG()">Скачать PNG</button>
                    <button class="btn-pdf" onclick="downloadPDF()">Скачать PDF</button>
                    <button class="btn-vk" onclick="shareVK()">ВКонтакте</button>
                    <button class="btn-telegram" onclick="shareTelegram()">Telegram</button>
                    <button class="btn-whatsapp" onclick="shareWhatsApp()">WhatsApp</button>
                    <button class="btn-email" onclick="shareEmail()">Email</button>
                    <button class="btn-copy" onclick="copyLink()">Копировать ссылку</button>
                </div>
                <div class="share-link-box">
                    <input type="text" id="shareUrl" value="{request.url}" readonly>
                    <button class="btn-copy" onclick="copyLink()">Копировать</button>
                </div>
                <div id="successMsg" class="success-message">✅ Ссылка скопирована!</div>
            </div>
            <script>
                const shareUrl = document.getElementById('shareUrl').value;
                const pdfUrl = "{pdf_url}";
                const studentName = "{share_record.student_name}";
                const courseName = "{share_record.course_name}";
                function downloadPDF() {{ window.location.href = pdfUrl; }}
                function downloadPNG() {{
                    const img = document.querySelector('img');
                    const link = document.createElement('a');
                    link.href = img.src;
                    link.download = 'report.png';
                    link.click();
                }}
                function shareVK() {{
                    window.open(`https://vk.com/share.php?url=${{encodeURIComponent(shareUrl)}}&title=${{encodeURIComponent(`Мой отчёт по курсу "${{courseName}}"`)}}`, '_blank');
                }}
                function shareTelegram() {{
                    window.open(`https://t.me/share/url?url=${{shareUrl}}&text=${{encodeURIComponent(`Посмотри мой отчёт по курсу "${{courseName}}"!`)}}`, '_blank');
                }}
                function shareWhatsApp() {{
                    window.open(`https://wa.me/?text=${{encodeURIComponent(`Посмотри мой отчёт по курсу "${{courseName}}"!\n\nСсылка: ${{shareUrl}}`)}}`, '_blank');
                }}
                function shareEmail() {{
                    window.location.href = `mailto:?subject=${{encodeURIComponent(`Мой отчёт по курсу "${{courseName}}"`)}}&body=${{encodeURIComponent(`Посмотри мой отчёт!\n\nСсылка: ${{shareUrl}}\n\nС уважением, ${{studentName}}`)}}`;
                }}
                function copyLink() {{
                    navigator.clipboard.writeText(shareUrl).then(() => {{
                        const msg = document.getElementById('successMsg');
                        msg.style.display = 'block';
                        setTimeout(() => msg.style.display = 'none', 2000);
                    }});
                }}
            </script>
        </body>
        </html>
        ''')
    finally:
        db.close()

@app.route('/api/download-pdf/<token>')
def download_pdf(token):
    if token in report_gen.cache_paths:
        pdf_path = report_gen.cache_paths[token][1]
        return send_file(pdf_path, as_attachment=True,
                        download_name=f"report_{token}.pdf",
                        mimetype='application/pdf')
    return "Файл не найден", 404

@app.route('/static/reports/<filename>')
def serve_report_image(filename):
    from flask import send_from_directory
    return send_from_directory('share_cache/', filename)

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Certify Real</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
                min-height: 100vh;
            }
            .header {
                background: rgba(15, 23, 42, 0.95);
                padding: 20px 40px;
                border-bottom: 1px solid #334155;
            }
            .header-content {
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 20px;
            }
            .logo {
                font-size: 28px;
                font-weight: bold;
                color: #38BDF8;
            }
            .logo span { color: #F97316; }
            .nav a {
                color: #94A3B8;
                text-decoration: none;
                margin-left: 30px;
            }
            .nav a:hover { color: #38BDF8; }
            .container { max-width: 1200px; margin: 0 auto; padding: 40px; }
            .hero {
                text-align: center;
                margin-bottom: 60px;
            }
            .hero h1 {
                font-size: 48px;
                color: #F1F5F9;
                margin-bottom: 20px;
            }
            .hero p {
                font-size: 20px;
                color: #94A3B8;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 24px;
                margin-bottom: 60px;
            }
            .stat-card {
                background: #1E293B;
                border-radius: 20px;
                padding: 28px 24px;
                text-align: center;
                border: 1px solid #334155;
            }
            .stat-title {
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
                color: #38BDF8;
            }
            .stat-text {
                color: #94A3B8;
                font-size: 15px;
                line-height: 1.6;
            }
            .age-stats {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 24px;
                margin-bottom: 60px;
            }
            .age-card {
                background: #1E293B;
                border-radius: 20px;
                padding: 24px;
                text-align: center;
                border: 1px solid #334155;
            }
            .age-card.primary { border-top: 4px solid #10B981; }
            .age-card.senior { border-top: 4px solid #F97316; }
            .age-title {
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 16px;
            }
            .age-title.primary { color: #10B981; }
            .age-title.senior { color: #F97316; }
            .age-desc {
                color: #94A3B8;
                font-size: 14px;
                line-height: 1.5;
            }
            .action-card {
                background: #1E293B;
                border-radius: 20px;
                padding: 40px;
                text-align: center;
                border: 1px solid #334155;
            }
            .action-card h3 { color: #F1F5F9; font-size: 24px; margin-bottom: 16px; }
            .action-card p { color: #94A3B8; margin-bottom: 24px; }
            .btn-test {
                background: #38BDF8;
                color: #0F172A;
                padding: 12px 32px;
                border-radius: 40px;
                text-decoration: none;
                font-weight: bold;
                display: inline-block;
            }
            .btn-test:hover { background: #F97316; }
            .footer {
                text-align: center;
                padding: 40px;
                color: #64748B;
                border-top: 1px solid #334155;
                margin-top: 60px;
            }
            @media (max-width: 768px) {
                .stats-grid { grid-template-columns: repeat(2, 1fr); }
                .age-stats { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <div class="logo">Certify<span>Real</span></div>
                <div class="nav">
                    <a href="/">Главная</a>
                    <a href="/test">Тестовая страница</a>
                    <a href="/api/students">API</a>
                </div>
            </div>
        </div>
        
        <div class="container">
            <div class="hero">
                <h1>Certify Real</h1>
                <p>Персонализированные отчёты на основе реальных метрик</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title">Знания открывают двери</div>
                    <div class="stat-text">Каждый новый навык делает тебя увереннее и расширяет твои возможности в будущем.</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Учёба развивает мышление</div>
                    <div class="stat-text">Решение задач тренирует мозг, учит анализировать и находить нестандартные решения.</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Знания = свобода выбора</div>
                    <div class="stat-text">Чем больше ты знаешь, тем больше профессий и путей тебе открыто.</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Успех начинается сегодня</div>
                    <div class="stat-text">Маленькие шаги каждый день приводят к большим результатам в будущем.</div>
                </div>
            </div>
            
            <div class="age-stats">
                <div class="age-card primary">
                    <div class="age-title primary">Путь динозаврика Дино</div>
                    <div class="age-desc">Приключение начинается! Каждое задание — новый шаг вперёд. Учись, играй и расти вместе с Дино!</div>
                </div>
                <div class="age-card senior">
                    <div class="age-title senior">Школа — это только стартовая площадка</div>
                    <div class="age-desc">Твои знания и навыки сегодня — фундамент для великих достижений завтра. Продолжай учиться и мечтать!</div>
                </div>
            </div>
            
            <div class="action-card">
                <h3>Создать сертификат</h3>
                <p>Перейдите на тестовую страницу, чтобы создать сертификат для любого ученика</p>
                <a href="/test" class="btn-test">Перейти к тесту →</a>
            </div>
        </div>
        
        <div class="footer">
            <p>Certify Real — персонализированные отчёты на основе реальных метрик</p>
        </div>
    </body>
    </html>
    ''')

@app.route('/test')
def test_page():
    students = get_all_students_list()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Тестовая страница - Certify Real</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
                min-height: 100vh;
            }
            .header {
                background: rgba(15, 23, 42, 0.95);
                padding: 20px 40px;
                border-bottom: 1px solid #334155;
            }
            .header-content {
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .logo {
                font-size: 28px;
                font-weight: bold;
                color: #38BDF8;
            }
            .logo span { color: #F97316; }
            .nav a {
                color: #94A3B8;
                text-decoration: none;
                margin-left: 30px;
            }
            .container { max-width: 500px; margin: 0 auto; padding: 40px 20px; }
            .card {
                background: #1E293B;
                border-radius: 24px;
                padding: 32px;
                border: 1px solid #334155;
            }
            .card h1 { color: #F1F5F9; font-size: 28px; margin-bottom: 8px; }
            .card .subtitle { color: #94A3B8; margin-bottom: 24px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; color: #94A3B8; margin-bottom: 8px; }
            input {
                width: 100%;
                padding: 12px;
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 12px;
                color: white;
            }
            button {
                width: 100%;
                padding: 14px;
                background: #38BDF8;
                border: none;
                border-radius: 40px;
                font-weight: bold;
                cursor: pointer;
            }
            button:hover { background: #F97316; }
            .result {
                margin-top: 24px;
                padding: 20px;
                background: #0F172A;
                border-radius: 16px;
                word-break: break-all;
                color: #F1F5F9;
            }
            .result a { color: #38BDF8; }
            .result strong { color: #10B981; }
            .student-list {
                background: #0F172A;
                border-radius: 16px;
                padding: 16px;
                margin-bottom: 24px;
            }
            .student-item {
                padding: 8px;
                border-bottom: 1px solid #334155;
                color: #94A3B8;
            }
            .footer {
                text-align: center;
                padding: 40px;
                color: #64748B;
                border-top: 1px solid #334155;
                margin-top: 40px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <div class="logo">Certify<span>Real</span></div>
                <div class="nav">
                    <a href="/">Главная</a>
                    <a href="/test">Тестовая страница</a>
                </div>
            </div>
        </div>
        
        <div class="container">
            <div class="card">
                <h1>Создать сертификат</h1>
                <div class="subtitle">Введите ID ученика</div>
                
                <div class="student-list">
                    <div style="color: #F1F5F9; margin-bottom: 8px;">Доступные ученики:</div>
                    {% for student in students %}
                    <div class="student-item">ID {{ student.id }}</div>
                    {% endfor %}
                </div>
                
                <form id="certForm">
                    <div class="form-group">
                        <label>ID ученика</label>
                        <input type="number" id="studentId" placeholder="1, 2, 3..." required>
                    </div>
                    <button type="submit">Создать сертификат</button>
                </form>
                
                <div id="result" class="result" style="display: none;"></div>
            </div>
        </div>
        
        <div class="footer">
            <p>Certify Real — персонализированные отчёты</p>
        </div>
        
        <script>
            document.getElementById('certForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const studentId = document.getElementById('studentId').value;
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = 'Генерация...';
                
                try {
                    const response = await fetch('/api/share/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id: parseInt(studentId) })
                    });
                    const data = await response.json();
                    if (response.ok) {
                        resultDiv.innerHTML = `<strong>✅ Готово!</strong><br><a href="${data.share_link}" target="_blank">${data.share_link}</a>`;
                    } else {
                        resultDiv.innerHTML = `<strong>❌ Ошибка:</strong> ${data.error}`;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `<strong>❌ Ошибка:</strong> ${error.message}`;
                }
            });
        </script>
    </body>
    </html>
    ''', students=students)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print("\n" + "="*50)
    print(f"Сервер запущен: http://localhost:{port}")
    print(f"Тест: http://localhost:{port}/test")
    print("="*50)
    app.run(host='0.0.0.0', port=port, debug=True)