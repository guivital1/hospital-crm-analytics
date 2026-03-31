class PacienteDuplicadoError(Exception):
    def __init__(self):
        super().__init__("CPF ou e-mail já cadastrado.")

class LeadDuplicadoError(Exception):
    def __init__(self):
        super().__init__("Lead com mesmo telefone ou e-mail já existe.")