!pip install python-docx
!pip install pdfplumber
import os
from docx import Document
import gdown
import pdfplumber
import re
import spacy
import nltk
nltk.download('punkt_tab')
nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
nlp = spacy.load("en_core_web_sm")
from sentence_transformers import SentenceTransformer, util
import spacy.cli
spacy.cli.download("en_core_web_sm")

def read_file_content(file_path):
  text = ""
  try:
    #تحديد نوع الملف
    file_extension = os.path.splitext(file_path)[1].lower()
    #التعامل مع ملفات pdf
    if file_extension == '.pdf':
      with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
          text += page.extract_text()
      return text
    #التعامل مع ملفات وورد
    elif file_extension == '.docx':
      doc = Document(file_path)
      text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
      return text
    #الملفات غير المقبولة
    else:
      return "نوع الملف غير مدعوم. الرجاء استخدام ملف PDF أو Word (docx/doc)."

  except Exception as e:
    return f"حدث خطأ أثناء قراءة الملف: {str(e)}"

def clean_text(text):
    text = re.sub(r'[^\w\s]', '', text)  # إزالة علامات الترقيم
    text = text.lower()  # تحويل إلى أحرف صغيرة
    if text and isinstance(text, str):
      tokens = word_tokenize(text) # تقسيم النص إلى كلمات
    else:
      print("النص غير صالح أو فارغ!")
    stop_words = set(stopwords.words('arabic', 'english'))  # كلمات شائعة
    filtered_tokens = [word for word in tokens if word not in stop_words]
    return " ".join(filtered_tokens)

def extract_keywords_spacy(text):
    doc = nlp(text)
    keywords = [token.text for token in doc
        if token.pos_ in ["NOUN", "VERB"] and len(token.text) > 2 ]
    keywords += [chunk.text for chunk in doc.noun_chunks]
    return keywords


def calculate_similarity(text1, text2):
    embedding1 = model.encode(text1, convert_to_tensor=True)
    embedding2 = model.encode(text2, convert_to_tensor=True)
    similarity = util.pytorch_cos_sim(embedding1, embedding2)
    return similarity.item()

gd_cv = gdown.download("https://drive.google.com/uc?id=1SdEppCjEQbRPiLGsIyNMxyWotuMECjPF")
gd_des= gdown.download("https://drive.google.com/uc?id=1k2VSgR_pIYmAdfBISYyvEwjC8rvtlkEm")

read_cv= read_file_content(gd_cv)
clean_cv=clean_text(read_cv)
cv= extract_keywords_spacy(clean_cv)

read_des =read_file_content(gd_des)
clean_des= clean_text(read_des)
job_describtion = extract_keywords_spacy(read_des)


model = SentenceTransformer('bert-large-uncased-whole-word-masking-finetuned-squad')
similarity_score = calculate_similarity(clean_cv, clean_des)
print(f"درجة المطابقة: {similarity_score * 100:.2f}%")
