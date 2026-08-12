import logging
import shutil

from flask import Flask, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge
from PIL import Image, UnidentifiedImageError
import pytesseract
import io
import pdfplumber
from pdf2image import convert_from_bytes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POPPLER_PATH = None #modificar para usar diretamente na máquina
EXTENSOES_IMAGEM = (".png", ".jpg", ".jpeg")
EXTENSOES_PDF = (".pdf",)

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

def verificar_dependencias():
    problemas = []
    
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        problemas.append(
            "Tesseract OCR não encontrado. Instale com "
            "'sudo apt install tesseract-ocr tesseract-ocr-por' (Linux) "
            "ou baixe o instalador oficial (Windows/Mac)."
        )
        
    if shutil.which("pdftoppm") is None and POPPLER_PATH is None:
        problemas.append(
            "Poppler não encontrado no PATH. Instale com "
            "'sudo apt install poppler-utils' (Linux), 'brew install poppler' (Mac) "
            "ou defina POPPLER_PATH apontando para a pasta 'bin' do Poppler (Windows)."
        )
    
    if problemas:
        for p in problemas:
            logger.warning("Dependências ausentes: %s", p)
    else:
        logger.info("Tesseract e Poppler encontrados com sucesso.")
        
        
verificar_dependencias()


def extensao_valida(nome_arquivo, extensoes):
    return nome_arquivo.lower().endswith(extensoes)


def processar_imagem(arquivo_bytes):
    imagem = Image.open(io.BytesIO(arquivo_bytes))
    imagem.load()
    return pytesseract.image_to_string(imagem, lang="por")


def processar_pdf(pdf_bytes):
    texto = ""
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pagina in pdf.pages:
            conteudo = pagina.extract_text()
            if conteudo:
                texto += conteudo + "\n"
    
    if texto.strip():
        return texto
    
    kwargs = {"dpi": 300}
    if POPPLER_PATH:
        kwargs["poppler_path"] = POPPLER_PATH
        
    paginas = convert_from_bytes(pdf_bytes, **kwargs)
    for pagina in paginas:
        texto += pytesseract.image_to_string(pagina, lang="por") + "\n"
        
    return texto



@app.errorhandler(RequestEntityTooLarge)
def arquivo_muito_grande(_erro):
    return render_template(
        "index.html",
        texto="Arquivo muito grande. Limitado a  16MB",
        encontrado=False,
    ), 413
    
 
@app.route("/", methods=["GET", "POST"])

def index():
    texto = None 
    encontrado = False
    
    if request.method == "POST": 
        arquivo = request.files.get("arquivo") 
        
        if arquivo and arquivo.filename:
            nome = arquivo.filename
            
            try:
                if extensao_valida(nome, EXTENSOES_IMAGEM):
                    texto = processar_imagem(arquivo.read())
                    encontrado = bool(texto.strip())
                    if not encontrado:
                        texto = "Nenhum texto encontrado na imagem."
                        
                elif extensao_valida(nome, EXTENSOES_PDF):
                    texto = processar_pdf(arquivo.read())
                    encontrado = bool(texto.strip())
                    if not encontrado:
                        texto = "Nenhum texto encontrado no PDF."
                        
                else:
                    texto = "Formato não suportado. Envie um arquivo PNG, JPG ou PDF."
                    encontrado = False
            
            except UnidentifiedImageError:
                logger.warning("Arquivo de imagem inválido: %s", nome)
                texto = "Não foi possível ler essa imagem. Verifique se o arquivo não está corrompido."
                
            except Exception:
                logger.exception("Erro ao processar arquivo: %s", nome)
                texto = "Ocorreu um erro ao processar o arquivo. Tente novamente."
                
    return render_template("index.html", texto=texto, encontrado=encontrado)


if __name__ == "__main__":
    app.run(debug=False)