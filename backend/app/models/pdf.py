from enum import StrEnum


GENERATED_PDF_COLLECTION = "generated_pdfs"


class PDFGenerationType(StrEnum):
    """
    Model describing the pdf generation type domain object.
    """
    ANONYMOUS = "ANONYMOUS"
    AUTHENTICATED = "AUTHENTICATED"


class PDFOwnerType(StrEnum):
    """
    Model describing the pdf owner type domain object.
    """
    ANONYMOUS = "ANONYMOUS"
    USER = "USER"
