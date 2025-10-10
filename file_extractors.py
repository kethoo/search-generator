from PyPDF2 import PdfReader
import mammoth

def extract_text_from_file(uploaded_file):
    file_type = uploaded_file.type

    if file_type == "text/plain":
        return uploaded_file.read().decode("utf-8")

    elif file_type == "application/pdf":
        reader = PdfReader(uploaded_file)
        return "\n".join(
            [page.extract_text() for page in reader.pages if page.extract_text()]
        )

    elif file_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ]:
        result = mammoth.extract_raw_text(uploaded_file)
        return result.value

    else:
        return "Unsupported file type."
