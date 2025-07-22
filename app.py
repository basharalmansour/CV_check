import os
from flask import Flask, request, render_template_string, jsonify
from werkzeug.utils import secure_filename
from docx import Document
import pdfplumber
import re
import spacy
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sentence_transformers import SentenceTransformer, util
from flask_cors import CORS

# تنزيل بيانات NLTK المطلوبة
nltk.download('punkt')
nltk.download('stopwords')

# تحميل نموذج spaCy
try:
    nlp = spacy.load("en_core_web_sm")
except:
    # إذا لم يكن النموذج مثبتاً
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'doc'}

# إنشاء مجلد التحميل إذا لم يكن موجودًا
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# HTML template مضمن في الكود
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مطابقة السيرة الذاتية مع الوظيفة</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="file"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        button {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            display: block;
            width: 100%;
            margin-top: 20px;
        }
        button:hover {
            background-color: #2980b9;
        }
        #result {
            margin-top: 20px;
            padding: 15px;
            border-radius: 4px;
            display: none;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .progress {
            text-align: center;
            margin: 20px 0;
            display: none;
        }
        .progress-bar {
            width: 100%;
            background-color: #e0e0e0;
            border-radius: 4px;
            margin-bottom: 10px;
        }
        .progress-bar-fill {
            height: 20px;
            background-color: #3498db;
            border-radius: 4px;
            width: 0%;
            transition: width 0.3s;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>مطابقة السيرة الذاتية مع الوظيفة</h1>
        <form id="uploadForm" enctype="multipart/form-data">
            <div class="form-group">
                <label for="cv">رفع السيرة الذاتية (PDF أو Word)</label>
                <input type="file" id="cv" name="cv" accept=".pdf,.doc,.docx" required>
            </div>
            <div class="form-group">
                <label for="job_description">رفع وصف الوظيفة (PDF أو Word)</label>
                <input type="file" id="job_description" name="job_description" accept=".pdf,.doc,.docx" required>
            </div>
            <button type="submit">تحليل المطابقة</button>
        </form>
        
        <div class="progress" id="progress">
            <div class="progress-bar">
                <div class="progress-bar-fill" id="progressBar"></div>
            </div>
            <div id="progressText">جاري معالجة الملفات...</div>
        </div>
        
        <div id="result"></div>
    </div>

    <script>
        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const form = e.target;
            const formData = new FormData(form);
            const resultDiv = document.getElementById('result');
            const progressDiv = document.getElementById('progress');
            const progressBar = document.getElementById('progressBar');
            const progressText = document.getElementById('progressText');
            
            // إظهار شريط التقدم وإخفاء النتائج السابقة
            progressDiv.style.display = 'block';
            resultDiv.style.display = 'none';
            
            // محاكاة التقدم
            let progress = 0;
            const interval = setInterval(() => {
                progress += 5;
                progressBar.style.width = `${Math.min(progress, 90)}%`;
                if (progress >= 90) clearInterval(interval);
            }, 300);
            
            fetch('/analyze', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                clearInterval(interval);
                progressBar.style.width = '100%';
                progressText.textContent = 'تم الانتهاء!';
                
                setTimeout(() => {
                    progressDiv.style.display = 'none';
                    
                    if (data.error) {
                        resultDiv.innerHTML = `<div class="error">${data.error}</div>`;
                    } else {
                        resultDiv.innerHTML = `
                            <div class="success">
                                <h3>نتيجة المطابقة:</h3>
                                <p>درجة المطابقة بين السيرة الذاتية ووصف الوظيفة: <strong>${data.similarity_score}%</strong></p>
                                <h4>الكلمات المفتاحية في السيرة الذاتية:</h4>
                                <p>${data.cv_keywords.join(', ')}</p>
                                <h4>الكلمات المفتاحية في وصف الوظيفة:</h4>
                                <p>${data.job_keywords.join(', ')}</p>
                            </div>
                        `;
                    }
                    resultDiv.style.display = 'block';
                }, 1000);
            })
            .catch(error => {
                clearInterval(interval);
                progressDiv.style.display = 'none';
                resultDiv.innerHTML = `<div class="error">حدث خطأ أثناء معالجة الطلب: ${error.message}</div>`;
                resultDiv.style.display = 'block';
            });
        });
    </script>
</body>
</html>
"""

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def read_file_content(file_path):
    text = ""
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        
        elif file_extension == '.docx':
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        
        else:
            return None
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        return None

def clean_text(text):
    if not text:
        return ""
    
    text = re.sub(r'[^\w\s]', '', text)  # إزالة علامات الترقيم
    text = text.lower()  # تحويل إلى أحرف صغيرة
    
    # دمج قائمة停用 words من اللغتين العربية والإنجليزية
    stop_words = set(stopwords.words('arabic')).union(set(stopwords.words('english')))
    
    tokens = word_tokenize(text)  # تقسيم النص إلى كلمات
    filtered_tokens = [word for word in tokens if word not in stop_words and len(word) > 2]
    return " ".join(filtered_tokens)

def extract_keywords_spacy(text):
    if not text:
        return []
    
    doc = nlp(text)
    keywords = [token.text for token in doc if token.pos_ in ["NOUN", "VERB"] and len(token.text) > 2]
    keywords += [chunk.text for chunk in doc.noun_chunks]
    return list(set(keywords))  # إزالة التكرارات

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'cv' not in request.files or 'job_description' not in request.files:
        return jsonify({'error': 'الرجاء تحميل الملفين المطلوبين'}), 400
    
    cv_file = request.files['cv']
    job_file = request.files['job_description']
    
    if cv_file.filename == '' or job_file.filename == '':
        return jsonify({'error': 'لم يتم اختيار ملف'}), 400
    
    if not (allowed_file(cv_file.filename) and allowed_file(job_file.filename)):
        return jsonify({'error': 'نوع الملف غير مدعوم. الرجاء استخدام ملف PDF أو Word'}), 400
    
    try:
        # حفظ الملفات مؤقتاً
        cv_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(cv_file.filename))
        job_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(job_file.filename))
        
        cv_file.save(cv_path)
        job_file.save(job_path)
        
        # قراءة المحتوى
        read_cv = read_file_content(cv_path)
        read_des = read_file_content(job_path)
        
        if not read_cv or not read_des:
            return jsonify({'error': 'تعذر قراءة محتوى الملفات. تأكد من أنها غير محمية بكلمة مرور'}), 400
        
        # تنظيف النص
        clean_cv = clean_text(read_cv)
        clean_des = clean_text(read_des)
        
        # استخراج الكلمات المفتاحية
        cv_keywords = extract_keywords_spacy(clean_cv)
        job_keywords = extract_keywords_spacy(clean_des)
        
        # حساب التشابه
        model = SentenceTransformer('bert-large-uncased-whole-word-masking-finetuned-squad')  
        similarity_score = util.pytorch_cos_sim(
            model.encode(clean_cv, convert_to_tensor=True),
            model.encode(clean_des, convert_to_tensor=True)
        ).item()
        
        similarity_percentage = round(similarity_score * 100, 2)
        
        # حذف الملفات المؤقتة
        os.remove(cv_path)
        os.remove(job_path)
        
        return jsonify({
            'similarity_score': similarity_percentage,
            'cv_keywords': cv_keywords,
            'job_keywords': job_keywords
        })
        
    except Exception as e:
        return jsonify({'error': f'حدث خطأ أثناء المعالجة: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
