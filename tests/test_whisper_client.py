#!/usr/bin/env python3
"""
Tests unitarios para WhisperClient — Fase 2
Generado por: @tdd-architect
Basado en: docs/tasks/phase-2-worker.md § Tarea 2.1

Uso:
    cd /path/to/whisper-local
    python -m pytest tests/test_whisper_client.py -v
"""

import sys
import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock

# Añadir src/ al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestWhisperClientInit:
    """Tests para inicialización de WhisperClient."""

    def test_init_with_default_timeout(self):
        """
        ESCENARIO: Crear instancia con host y port solamente.
        COMPORTAMIENTO: Almacena host, port y usa timeout=300 por defecto.
        PROPÓSITO: Permitir configuración mínima del cliente.
        """
        from whisper_client import WhisperClient
        client = WhisperClient(host="localhost", port=8080)
        assert client.host == "localhost"
        assert client.port == 8080
        assert client.timeout == 300

    def test_init_with_custom_timeout(self):
        """
        ESCENARIO: Crear instancia con timeout personalizado.
        COMPORTAMIENTO: Almacena el timeout proporcionado.
        PROPÓSITO: Permitir configuración de timeout según necesidad.
        """
        from whisper_client import WhisperClient
        client = WhisperClient(host="localhost", port=8080, timeout=600)
        assert client.timeout == 600

    def test_init_creates_base_url(self):
        """
        ESCENARIO: Inicialización del cliente.
        COMPORTAMIENTO: Construye URL base correcta.
        PROPÓSITO: Facilitar construcción de endpoints.
        """
        from whisper_client import WhisperClient
        client = WhisperClient(host="localhost", port=8080)
        assert hasattr(client, 'base_url')
        assert client.base_url == "http://localhost:8080"


class TestWhisperClientHealthCheck:
    """Tests para health_check de WhisperClient."""

    @patch('whisper_client.requests.get')
    def test_health_check_success(self, mock_get):
        """
        ESCENARIO: Servidor responde 200 OK en /health.
        COMPORTAMIENTO: Retorna True.
        PROPÓSITO: Verificar disponibilidad del servidor whisper.
        """
        from whisper_client import WhisperClient
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = WhisperClient(host="localhost", port=8080)
        result = client.health_check()
        assert result is True

    @patch('whisper_client.requests.get')
    def test_health_check_failure_404(self, mock_get):
        """
        ESCENARIO: Servidor responde 404 Not Found.
        COMPORTAMIENTO: Retorna False.
        PROPÓSITO: Detectar cuando el endpoint no está disponible.
        """
        from whisper_client import WhisperClient
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        client = WhisperClient(host="localhost", port=8080)
        result = client.health_check()
        assert result is False

    @patch('whisper_client.requests.get')
    def test_health_check_failure_500(self, mock_get):
        """
        ESCENARIO: Servidor responde 500 Internal Server Error.
        COMPORTAMIENTO: Retorna False.
        PROPÓSITO: Detectar errores del servidor.
        """
        from whisper_client import WhisperClient
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        client = WhisperClient(host="localhost", port=8080)
        result = client.health_check()
        assert result is False

    @patch('whisper_client.requests.get')
    def test_health_check_uses_correct_endpoint(self, mock_get):
        """
        ESCENARIO: Llamada a health_check.
        COMPORTAMIENTO: Realiza GET a http://host:port/health.
        PROPÓSITO: Verificar que usa el endpoint correcto.
        """
        from whisper_client import WhisperClient
        mock_get.return_value = Mock(status_code=200)

        client = WhisperClient(host="localhost", port=8080)
        client.health_check()
        mock_get.assert_called_once()
        args = mock_get.call_args
        assert "localhost:8080/health" in args[0][0]

    @patch('whisper_client.requests.get')
    def test_health_check_connection_error(self, mock_get):
        """
        ESCENARIO: No se puede conectar al servidor.
        COMPORTAMIENTO: Lanza WhisperError.
        PROPÓSITO: Manejar errores de conexión de forma controlada.
        """
        from whisper_client import WhisperClient, WhisperError
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        client = WhisperClient(host="localhost", port=8080)
        with pytest.raises(WhisperError) as exc_info:
            client.health_check()
        assert "Connection refused" in str(exc_info.value)


class TestWhisperClientIsServerReady:
    """Tests para is_server_ready con retry logic."""

    @patch('whisper_client.requests.get')
    def test_server_ready_first_attempt(self, mock_get):
        """
        ESCENARIO: Servidor responde OK en primer intento.
        COMPORTAMIENTO: Retorna True inmediatamente sin retries.
        PROPÓSITO: Optimizar cuando servidor está disponible.
        """
        from whisper_client import WhisperClient
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = WhisperClient(host="localhost", port=8080)
        result = client.is_server_ready(retries=5)
        assert result is True
        assert mock_get.call_count == 1

    @patch('whisper_client.requests.get')
    def test_server_ready_after_retries(self, mock_get):
        """
        ESCENARIO: Servidor responde OK en tercer intento.
        COMPORTAMIENTO: Reintenta 3 veces, luego retorna True.
        PROPÓSITO: Permitir arranque gradual del servidor.
        """
        from whisper_client import WhisperClient
        import requests
        
        mock_get.side_effect = [
            requests.ConnectionError("Retry 1"),
            requests.ConnectionError("Retry 2"),
            Mock(status_code=200)
        ]

        client = WhisperClient(host="localhost", port=8080)
        result = client.is_server_ready(retries=5)
        assert result is True
        assert mock_get.call_count == 3

    @patch('whisper_client.time.sleep')
    @patch('whisper_client.requests.get')
    def test_server_ready_exhausts_retries(self, mock_get, mock_sleep):
        """
        ESCENARIO: Servidor nunca responde después de 5 retries.
        COMPORTAMIENTO: Retorna False después de agotar reintentos.
        PROPÓSITO: Evitar espera infinita.
        """
        from whisper_client import WhisperClient
        import requests
        mock_get.side_effect = requests.ConnectionError("Server down")

        client = WhisperClient(host="localhost", port=8080)
        result = client.is_server_ready(retries=5)
        assert result is False
        assert mock_get.call_count == 5

    @patch('whisper_client.time.sleep')
    @patch('whisper_client.requests.get')
    def test_server_ready_uses_backoff_delays(self, mock_get, mock_sleep):
        """
        ESCENARIO: Reintentos con backoff exponencial.
        COMPORTAMIENTO: Duerme 1s, 2s, 4s, 8s, 16s entre intentos.
        PROPÓSITO: No saturar el servidor con reintentos rápidos.
        """
        from whisper_client import WhisperClient
        import requests
        
        mock_get.side_effect = [
            requests.ConnectionError("Retry 1"),
            requests.ConnectionError("Retry 2"),
            requests.ConnectionError("Retry 3"),
            requests.ConnectionError("Retry 4"),
            requests.ConnectionError("Retry 5")
        ]

        client = WhisperClient(host="localhost", port=8080)
        client.is_server_ready(retries=5)
        
        # Verificar que se usaron los delays correctos
        expected_delays = [1, 2, 4, 8, 16]
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays


class TestWhisperClientTranscribe:
    """Tests para método transcribe."""

    @patch('whisper_client.requests.post')
    def test_transcribe_success(self, mock_post):
        """
        ESCENARIO: Audio válido, servidor responde con transcripción.
        COMPORTAMIENTO: Retorna texto extraído del campo 'text'.
        PROPÓSITO: Obtener transcripción del audio.
        """
        from whisper_client import WhisperClient
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Hola mundo"}
        mock_post.return_value = mock_response

        client = WhisperClient(host="localhost", port=8080)
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x24\x00\x00\x00WAVE")
            temp_path = f.name
        
        try:
            result = client.transcribe(temp_path, language='es')
            assert result == "Hola mundo"
        finally:
            os.unlink(temp_path)

    @patch('whisper_client.requests.post')
    def test_transcribe_uses_multipart_form(self, mock_post):
        """
        ESCENARIO: Llamada a transcribe con archivo de audio.
        COMPORTAMIENTO: Envía POST con Content-Type multipart/form-data.
        PROPÓSITO: Verificar formato correcto de la petición.
        """
        from whisper_client import WhisperClient
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "test"}
        mock_post.return_value = mock_response

        client = WhisperClient(host="localhost", port=8080)
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x24\x00\x00\x00WAVE")
            temp_path = f.name
        
        try:
            client.transcribe(temp_path, language='es')
            
            # Verificar que se llamó con files
            call_kwargs = mock_post.call_args[1]
            assert 'files' in call_kwargs or 'data' in call_kwargs
        finally:
            os.unlink(temp_path)

    @patch('whisper_client.requests.post')
    def test_transcribe_includes_language_parameter(self, mock_post):
        """
        ESCENARIO: Transcripción con idioma específico.
        COMPORTAMIENTO: Incluye parámetro 'language' en la petición.
        PROPÓSITO: Especificar idioma del audio.
        """
        from whisper_client import WhisperClient
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "hello"}
        mock_post.return_value = mock_response

        client = WhisperClient(host="localhost", port=8080)
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x24\x00\x00\x00WAVE")
            temp_path = f.name
        
        try:
            client.transcribe(temp_path, language='en')
            call_kwargs = mock_post.call_args[1]
            # Verificar que language está en los datos
            found = False
            if 'data' in call_kwargs:
                data = call_kwargs['data']
                if isinstance(data, dict) and 'language' in data:
                    found = True
            assert found, "Language parameter not found in request"
        finally:
            os.unlink(temp_path)

    @patch('whisper_client.requests.post')
    def test_transcribe_http_4xx_error(self, mock_post):
        """
        ESCENARIO: Servidor responde 400 Bad Request.
        COMPORTAMIENTO: Lanza WhisperError con detalle del error.
        PROPÓSITO: Manejar errores del cliente.
        """
        from whisper_client import WhisperClient, WhisperError
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid audio format"
        mock_post.return_value = mock_response

        client = WhisperClient(host="localhost", port=8080)
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x24\x00\x00\x00WAVE")
            temp_path = f.name
        
        try:
            with pytest.raises(WhisperError) as exc_info:
                client.transcribe(temp_path, language='es')
            assert "400" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    @patch('whisper_client.requests.post')
    def test_transcribe_http_5xx_error(self, mock_post):
        """
        ESCENARIO: Servidor responde 500 Internal Server Error.
        COMPORTAMIENTO: Lanza WhisperError con detalle del error.
        PROPÓSITO: Manejar errores del servidor.
        """
        from whisper_client import WhisperClient, WhisperError
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_post.return_value = mock_response

        client = WhisperClient(host="localhost", port=8080)
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x24\x00\x00\x00WAVE")
            temp_path = f.name
        
        try:
            with pytest.raises(WhisperError) as exc_info:
                client.transcribe(temp_path, language='es')
            assert "500" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    @patch('whisper_client.requests.post')
    def test_transcribe_invalid_json_response(self, mock_post):
        """
        ESCENARIO: Servidor responde con JSON inválido o sin campo 'text'.
        COMPORTAMIENTO: Lanza ParseError.
        PROPÓSITO: Manejar respuestas mal formadas del servidor.
        """
        from whisper_client import WhisperClient, ParseError
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "Bad response"}  # Sin campo 'text'
        mock_post.return_value = mock_response

        client = WhisperClient(host="localhost", port=8080)
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x24\x00\x00\x00WAVE")
            temp_path = f.name
        
        try:
            with pytest.raises(ParseError) as exc_info:
                client.transcribe(temp_path, language='es')
            assert "text" in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)

    @patch('whisper_client.requests.post')
    def test_transcribe_timeout(self, mock_post):
        """
        ESCENARIO: Transcripción toma más de 5 minutos.
        COMPORTAMIENTO: Lanza TimeoutError.
        PROPÓSITO: Evitar esperas indefinidas.
        """
        from whisper_client import WhisperClient, TimeoutError
        import requests
        mock_post.side_effect = requests.Timeout("Request timed out")

        client = WhisperClient(host="localhost", port=8080, timeout=300)
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x24\x00\x00\x00WAVE")
            temp_path = f.name
        
        try:
            with pytest.raises(TimeoutError) as exc_info:
                client.transcribe(temp_path, language='es')
            assert "timeout" in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)

    def test_transcribe_file_not_found(self):
        """
        ESCENARIO: Archivo de audio no existe.
        COMPORTAMIENTO: Lanza WhisperError indicando archivo no encontrado.
        PROPÓSITO: Validar existencia del archivo antes de enviar.
        """
        from whisper_client import WhisperClient, WhisperError
        client = WhisperClient(host="localhost", port=8080)
        
        with pytest.raises(WhisperError) as exc_info:
            client.transcribe("/nonexistent/audio.wav", language='es')
        assert "not found" in str(exc_info.value).lower() or "no existe" in str(exc_info.value).lower()


class TestWhisperClientErrorClasses:
    """Tests para las clases de error personalizadas."""

    def test_whisper_error_is_exception(self):
        """
        ESCENARIO: WhisperError hereda de Exception.
        COMPORTAMIENTO: Puede ser lanzada y capturada como excepción.
        PROPÓSITO: Permitir manejo de errores estándar.
        """
        from whisper_client import WhisperError
        assert issubclass(WhisperError, Exception)
        
        try:
            raise WhisperError("Test error")
        except Exception as e:
            assert str(e) == "Test error"

    def test_timeout_error_is_whisper_error(self):
        """
        ESCENARIO: TimeoutError hereda de WhisperError.
        COMPORTAMIENTO: TimeoutError es un tipo específico de WhisperError.
        PROPÓSITO: Jerarquía de errores para manejo específico.
        """
        from whisper_client import TimeoutError, WhisperError
        assert issubclass(TimeoutError, WhisperError)

    def test_parse_error_is_whisper_error(self):
        """
        ESCENARIO: ParseError hereda de WhisperError.
        COMPORTAMIENTO: ParseError es un tipo específico de WhisperError.
        PROPÓSITO: Jerarquía de errores para manejo específico.
        """
        from whisper_client import ParseError, WhisperError
        assert issubclass(ParseError, WhisperError)
