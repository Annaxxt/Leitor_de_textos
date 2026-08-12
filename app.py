from flask import Flask, render_template, request
from PIL import Image
import pytesseract
import io
import pdfplumber
from pdf2image import convert_from_bytes

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])

def index():
    
    texto = None 
    encontrado = False
    
    if request.method == "POST": 
        arquivo = request.files.get("arquivo") 
        
        if arquivo and arquivo.filename:
            
            if arquivo.filename.lower().endswith((".png", ".jpg", ".jpeg")): 
                imagem = Image.open(io.BytesIO(arquivo.read())) 
                texto = pytesseract.image_to_string(imagem) 
                
                if texto.strip():
                    encontrado = True
                    
            elif arquivo.filename.lower().endswith(".pdf"): 
                pdf_bytes = arquivo.read() 
                texto = "" 
                
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf: #tenta extrair o texto diretamente
                    for pagina in pdf.pages:
                        conteudo = pagina.extract_text()
                        if conteudo:
                            texto += conteudo + "\n"
                
                if not texto.strip(): #se não achar provavelmente é um PDF escaneado então converte as páginas para imagens
                    try:
                        paginas = convert_from_bytes(pdf_bytes) 
                    
                        for pagina in paginas:
                            texto += pytesseract.image_to_string(pagina) 
                    except Exception:
                       texto = "Não foi possível processar o PDF.\nVerifique se o Poppler está instalado." 
                        
                if texto.strip():
                    encontrado = True
                else:
                    texto = "Nenhum texto encontrado no PDF!"
            
    return render_template("index.html", texto=texto, encontrado=encontrado)

if __name__ == "__main__":
    app.run(debug=True) #deixar False quando for rodar o programa oficialmente