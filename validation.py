"""
Módulo de validação para melhorar feedback de formulários
"""
import re
from typing import Dict, List, Tuple, Any
from flask import flash


class ValidationError:
    """Representa um erro de validação específico para um campo"""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value


class ValidationResult:
    """Resultado de uma validação com erros específicos por campo"""
    def __init__(self):
        self.errors: List[ValidationError] = []
        self.is_valid = True
    
    def add_error(self, field: str, message: str, value: Any = None):
        """Adiciona um erro de validação"""
        self.errors.append(ValidationError(field, message, value))
        self.is_valid = False
    
    def get_field_errors(self, field: str) -> List[str]:
        """Retorna todas as mensagens de erro para um campo específico"""
        return [error.message for error in self.errors if error.field == field]
    
    def get_errors_dict(self) -> Dict[str, List[str]]:
        """Retorna um dicionário com erros agrupados por campo"""
        errors_dict = {}
        for error in self.errors:
            if error.field not in errors_dict:
                errors_dict[error.field] = []
            errors_dict[error.field].append(error.message)
        return errors_dict


class FormValidator:
    """Validador de formulários com regras específicas"""
    
    @staticmethod
    def validate_required(value: Any, field_name: str = "Campo") -> ValidationResult:
        """Valida se um campo obrigatório foi preenchido"""
        result = ValidationResult()
        if not value or (isinstance(value, str) and not value.strip()):
            result.add_error(field_name.lower(), f"{field_name} é obrigatório")
        return result
    
    @staticmethod
    def validate_string_length(value: str, min_length: int = None, max_length: int = None, field_name: str = "Campo") -> ValidationResult:
        """Valida o comprimento de uma string"""
        result = ValidationResult()
        if value:
            length = len(value.strip())
            if min_length and length < min_length:
                result.add_error(field_name.lower(), f"{field_name} deve ter pelo menos {min_length} caracteres")
            if max_length and length > max_length:
                result.add_error(field_name.lower(), f"{field_name} deve ter no máximo {max_length} caracteres")
        return result
    
    @staticmethod
    def validate_password_strength(password: str) -> ValidationResult:
        """Valida a força de uma senha"""
        result = ValidationResult()
        if not password:
            result.add_error("senha", "Senha é obrigatória")
            return result
        
        if len(password) < 6:
            result.add_error("senha", "Senha deve ter pelo menos 6 caracteres")
        
        if not re.search(r'[A-Za-z]', password):
            result.add_error("senha", "Senha deve conter pelo menos uma letra")
        
        if not re.search(r'\d', password):
            result.add_error("senha", "Senha deve conter pelo menos um número")
        
        return result
    
    @staticmethod
    def validate_username(username: str) -> ValidationResult:
        """Valida um nome de usuário"""
        result = ValidationResult()
        if not username:
            result.add_error("usuario", "Nome de usuário é obrigatório")
            return result
        
        username = username.strip()
        if len(username) < 3:
            result.add_error("usuario", "Nome de usuário deve ter pelo menos 3 caracteres")
        
        if len(username) > 50:
            result.add_error("usuario", "Nome de usuário deve ter no máximo 50 caracteres")
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            result.add_error("usuario", "Nome de usuário deve conter apenas letras, números e underscore")
        
        return result
    
    @staticmethod
    def validate_lotofacil_numbers(numbers: List[int]) -> ValidationResult:
        """Valida números da Lotofácil"""
        result = ValidationResult()
        
        if not numbers:
            result.add_error("numeros", "Selecione os números")
            return result
        
        if len(numbers) != 15:
            result.add_error("numeros", f"Selecione exatamente 15 números. Você selecionou {len(numbers)}")
        
        if len(set(numbers)) != len(numbers):
            result.add_error("numeros", "Não é possível repetir números")
        
        invalid_numbers = [n for n in numbers if n < 1 or n > 25]
        if invalid_numbers:
            result.add_error("numeros", f"Números inválidos: {', '.join(map(str, invalid_numbers))}. Use apenas números de 1 a 25")
        
        return result
    
    @staticmethod
    def validate_bolao_name(name: str) -> ValidationResult:
        """Valida nome de bolão"""
        result = ValidationResult()
        if not name or not name.strip():
            result.add_error("nome", "Nome do bolão é obrigatório")
            return result
        
        name = name.strip()
        if len(name) < 3:
            result.add_error("nome", "Nome do bolão deve ter pelo menos 3 caracteres")
        
        if len(name) > 100:
            result.add_error("nome", "Nome do bolão deve ter no máximo 100 caracteres")
        
        return result
    
    @staticmethod
    def validate_contest_number(number: str) -> ValidationResult:
        """Valida número do concurso"""
        result = ValidationResult()
        if number and number.strip():
            try:
                num = int(number.strip())
                if num <= 0:
                    result.add_error("numero_concurso", "Número do concurso deve ser positivo")
            except ValueError:
                result.add_error("numero_concurso", "Número do concurso deve ser um número válido")
        
        return result
    
    @staticmethod
    def validate_date_format(date_str: str, field_name: str = "data") -> ValidationResult:
        """Valida formato de data"""
        result = ValidationResult()
        if date_str and date_str.strip():
            try:
                from datetime import datetime
                datetime.fromisoformat(date_str.strip())
            except ValueError:
                result.add_error(field_name.lower(), f"{field_name} deve estar no formato válido (YYYY-MM-DD)")
        
        return result


def flash_validation_errors(validation_result: ValidationResult, category: str = "error"):
    """Adiciona erros de validação às mensagens flash do Flask"""
    for error in validation_result.errors:
        flash(f"{error.message}", category)


def get_validation_errors_for_template(validation_result: ValidationResult) -> Dict[str, List[str]]:
    """Retorna erros de validação formatados para uso em templates"""
    return validation_result.get_errors_dict()