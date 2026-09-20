"""
Luna JARVIS - Text Pre-Processor for Voice Clone
Optimizes text for better pronunciation in voice clone mode.

Key findings from experiments:
- Text WITHOUT accents produces best clarity (WER 37.5% vs 62-125%)
- Short sentences (<8 words) work better than long ones
- Standard punctuation (periods, commas) is fine
- Avoid exclamation marks
- Numbers should be spelled out
- English tech words need special handling
"""

import re
from typing import List


# Accent mapping for Spanish
ACCENT_MAP = {
    'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
    'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
    'ü': 'u', 'Ü': 'U',
    'ñ': 'n', 'Ñ': 'N',
}

# Number word mappings (Spanish)
NUMBER_WORDS = {
    '0': 'cero', '1': 'uno', '2': 'dos', '3': 'tres', '4': 'cuatro',
    '5': 'cinco', '6': 'seis', '7': 'siete', '8': 'ocho', '9': 'nueve',
    '10': 'diez', '11': 'once', '12': 'doce', '13': 'trece', '14': 'catorce',
    '15': 'quince', '16': 'dieciseis', '17': 'diecisiete', '18': 'dieciocho',
    '19': 'diecinueve', '20': 'veinte', '30': 'treinta', '40': 'cuarenta',
    '50': 'cincuenta', '60': 'sesenta', '70': 'setenta', '80': 'ochenta',
    '90': 'noventa', '100': 'cien', '1000': 'mil',
}

# Tech abbreviations and acronyms common in conversation
# Note: Keep commonly spoken English terms as-is (CPU, RAM, SSD, etc.)
# since Spanish expansions sound unnatural. Only expand what's truly unclear.
TECH_EXPANSIONS = {
    'GPU': 'tarjeta de video',
    'HDD': 'disco duro',
    'URL': 'enlace',
    'API': 'A P I',
    'HTML': 'H T M L',
    'CSS': 'C S S',
    'USB': 'U S B',
    'WiFi': 'wifi',
    'Wi-Fi': 'wifi',
    'VPN': 'V P N',
    'LED': 'L E D',
    'IA': 'inteligencia artificial',
    'AI': 'inteligencia artificial',
    'HTTPS': 'H T T P S',
    'HTTP': 'H T T P',
}

# Size units that need space before them and expansion
SIZE_UNITS = {
    'GB': 'gigabytes',
    'MB': 'megabytes',
    'KB': 'kilobytes',
    'TB': 'terabytes',
    'GHz': 'gigahercio',
    'MHz': 'megahercio',
}

# File extensions for pronunciation
FILE_EXTENSIONS = {
    '.py': 'punto pi y',
    '.js': 'punto jota ese',
    '.ts': 'punto te ese',
    '.java': 'punto java',
    '.html': 'punto html',
    '.css': 'punto cesés',
    '.json': 'punto jason',
    '.md': 'punto eme de',
    '.txt': 'punto texto',
    '.pdf': 'punto pideefe',
    '.exe': 'punto exe',
    '.dll': 'punto deelele',
    '.wav': 'punto uve doble a uve',
    '.mp3': 'punto eme pe tres',
    '.mp4': 'punto eme pe cuatro',
    '.zip': 'punto zip',
    '.rar': 'punto rar',
}

# Common abbreviations that should be expanded for TTS clarity
ABBREVIATIONS = {
    'Dr.': 'Doctor',
    'Dra.': 'Doctora',
    'Sr.': 'Senor',
    'Sra.': 'Senora',
    'Srta.': 'Senorita',
    'Prof.': 'Profesor',
    'Prof(a).': 'Profesora',
    'Ing.': 'Ingeniero',
    'Lic.': 'Licenciado',
    'Arq.': 'Arquitecto',
    'etc.': 'etcetera',
    'etcétera': 'etcetera',
    'vs.': 'versus',
    'vs': 'versus',
    'p.ej.': 'por ejemplo',
    'p. ej.': 'por ejemplo',
    'ej.': 'ejemplo',
    'Ej.': 'Ejemplo',
    'nro.': 'numero',
    'Nro.': 'Numero',
    'N°': 'numero',
    'n°': 'numero',
    'Av.': 'Avenida',
    'av.': 'avenida',
    'Pza.': 'Plaza',
    'Cia.': 'Compania',
    'cta.': 'cuenta',
    'tel.': 'telefono',
    'Tel.': 'Telefono',
    'dir.': 'direccion',
    'Dir.': 'Direccion',
    'attn.': 'atencion',
    'Attn.': 'Atencion',
    'pag.': 'pagina',
    'Pag.': 'Pagina',
    'pág.': 'pagina',
    'ref.': 'referencia',
    'Ref.': 'Referencia',
    'ejm.': 'ejemplo',
    'Ejm.': 'Ejemplo',
}

# Symbol expansions for spoken speech
SYMBOL_EXPANSIONS = {
    '&': ' y ',
    '@': ' arroba ',
    '=': ' igual a ',
    '+': ' mas ',
    '-': ' menos ',
    '*': ' por ',
    '/': ' dividido por ',
    '\\': ' barra ',
    '<': ' menor que ',
    '>': ' mayor que ',
    '<=': ' menor o igual que ',
    '>=': ' mayor o igual que ',
    '!=': ' diferente de ',
    '==': ' igual igual a ',
    '->': ' flecha ',
    '=>': ' implica ',
    '°': ' grados ',
    '€': ' euros ',
    '$': ' pesos ',
    '£': ' libras ',
    '©': ' copyright ',
    '®': ' registrado ',
    '™': ' marca registrada ',
}

# V5: Words that need emphasis (important terms get subtle markers)
# These are words that should be spoken with slightly more energy/clarity
EMPHASIS_WORDS = {
    # Time-sensitive words
    'ahora', 'urgente', 'importante', 'atencion', 'cuidado',
    'rapido', 'nuevo', 'nueva', 'actualizar', 'error',
    # Numbers and quantities
    'mucho', 'poco', 'todo', 'nada', 'todos', 'todas',
    # Key action words
    'abre', 'cierra', 'guarda', 'elimina', 'crea', 'busca',
    # Emotional emphasis
    'increible', 'genial', 'perfecto', 'excelente', 'horrible',
}

# V5: Sentence-type prosody markers
# Different sentence endings produce different intonation patterns
SENTENCE_PROSODY = {
    'question': {
        'markers': ['?', '¿'],
        'prefix': '',  # No prefix needed, TTS handles ? intonation
        'suffix': '',
    },
    'exclamation': {
        'markers': ['!', '¡'],
        'prefix': '',
        'suffix': '',
    },
    'statement': {
        'markers': ['.'],
        'prefix': '',
        'suffix': '',
    },
}

# V5: Context-aware pronunciation rules
# Words that change pronunciation based on surrounding context
CONTEXT_RULES = {
    # 'que' as conjunction vs 'qué' as interrogative
    # In voice clone, 'que' is fine — no respelling needed
    # 'cual' vs 'cuál' — same, leave as-is for natural sound
    # Numbers before units get special treatment (handled in expand_numbers)
}

# V5: Common phrases that sound better as single units
# These are multi-word expressions that TTS handles better together
NATURAL_PHRASES = {
    'buenos dias': 'buenos dias',
    'buenas tardes': 'buenas tardes',
    'buenas noches': 'buenas noches',
    'de nada': 'de nada',
    'por favor': 'por favor',
    'muchas gracias': 'muchas gracias',
    'lo siento': 'lo siento',
    'no te preocupes': 'no te preocupes',
    'esta bien': 'esta bien',
    'como estas': 'como estas',
    'que tal': 'que tal',
}

# V5: Speed hint markers for different content types
# Inserts subtle pause markers to control TTS rhythm
SPEED_HINTS = {
    'fast': [],  # Technical lists, enumerations
    'normal': [],  # Regular conversation
    'slow': [],  # Important information, warnings
}

# ASR respelling dictionary — proper nouns and custom terms that ASR
# consistently misrecognizes. Applied as post-processing on ASR output.
# Maps common misrecognitions -> correct form.
ASR_RESPELLING = {
    # User nicknames
    'de kov': 'Dekov',
    'dekov': 'Dekov',
    'the kov': 'Dekov',
    'de cob': 'Dekov',
    'de kop': 'Dekov',
    'sallo sin': 'Salocin',
    'salocin': 'Salocin',
    'sallo cin': 'Salocin',
    'sal oci': 'Salocin',
    'sala sin': 'Salocin',
    # Tech terms ASR struggles with
    'open claw': 'OpenClaw',
    'open clau': 'OpenClaw',
    'mi mo': 'MiMo',
    'mimo': 'MiMo',
    'luna jarvis': 'Luna JARVIS',
    'jarvis': 'JARVIS',
    'electron': 'Electron',
    'three js': 'Three.js',
    'three j s': 'Three.js',
    'chroma db': 'ChromaDB',
    'chroma d b': 'ChromaDB',
}


def fix_asr_names(text: str) -> str:
    """Post-process ASR output to fix common misrecognitions of proper nouns.

    Case-insensitive matching, preserves surrounding punctuation.
    """
    if not text:
        return text
    import re as _re
    for wrong, correct in sorted(ASR_RESPELLING.items(), key=lambda x: -len(x[0])):
        pattern = _re.compile(r'\b' + _re.escape(wrong) + r'\b', _re.IGNORECASE)
        text = pattern.sub(correct, text, count=1)
    return text


# Phonetic respelling for words that TTS consistently mispronounces
# These are Spanish words that voice clone models struggle with
PHONETIC_RESPELLING = {
    # Words with 'h' (silent in Spanish but TTS sometimes aspirates)
    'hola': 'ola',
    'hasta': 'asta',
    'hacer': 'aser',
    'hora': 'ora',
    'hoy': 'oy',
    'hay': 'ay',
    'hecho': 'echo',
    'hablar': 'ablar',
    'haber': 'aber',
    'hecho': 'echo',
    'historia': 'istoria',
    'hermano': 'ermano',
    'hermana': 'ermana',
    'humano': 'umano',
    'habitacion': 'abitacion',
    'horrible': 'orrible',
    'hospital': 'ospital',
    'hotel': 'otel',
    # Words with 'b/v' (same sound in Spanish, but TTS sometimes differentiates)
    'vivo': 'bibo',
    'verde': 'berde',
    'vamos': 'bamos',
    'verdad': 'berdad',
    'ventana': 'bentana',
    # Words with 'c/z' (Latin American 's' sound)
    'cerveza': 'serbesa',
    'zapato': 'sapato',
    'cielo': 'sielo',
    'cinco': 'sinco',
    # Difficult consonant clusters
    'psicologia': 'sicologia',
    'psicologo': 'sicologo',
    'pterodactilo': 'pterodactilo',
    'extra': 'ekstra',
    'examen': 'eksamen',
    'texto': 'teksto',
    'extremo': 'ekstremo',
    # NOTE: 'qu' words (que, quiero, porque, etc.) are NOT respelled.
    # Testing showed that 'ke', 'kiero', 'porke' produce WORSE voice clone
    # quality — the TTS model handles standard Spanish 'qu' naturally,
    # and the respelled forms cause ASR hallucination (WER >80%).
}

# Micro-pause markers for better rhythm in voice clone
# Inserts a very short pause (.) at natural clause boundaries
RHYTHM_BREAKS = {
    # After introductory phrases
    'bueno,': 'bueno., ',
    'entonces,': 'entonces., ',
    'ademas,': 'ademas., ',
    'sin embargo,': 'sin embargo., ',
    'por ejemplo,': 'por ejemplo., ',
    'en realidad,': 'en realidad., ',
    'la verdad,': 'la verdad., ',
    'o sea,': 'o sea., ',
    'es decir,': 'es decir., ',
    'en fin,': 'en fin., ',
}

# Common English words that TTS handles better in Spanish
ENGLISH_TO_SPANISH = {
    'okay': 'okey',
    'ok': 'okey',
    'hello': 'jol',
    'hi': 'jai',
    'thanks': 'gracias',
    'sorry': 'lo siento',
    'please': 'por favor',
    'yes': 'si',
    'no': 'no',
    'file': 'archivo',
    'folder': 'carpeta',
    'screen': 'pantalla',
    'mouse': 'raton',
    'keyboard': 'teclado',
    'browser': 'navegador',
    'download': 'descarga',
    'upload': 'subir',
    'click': 'clic',
    'scroll': 'desplazar',
    'tab': 'pestana',
    'window': 'ventana',
    'app': 'aplicacion',
    'software': 'software',
    'hardware': 'hardware',
    'server': 'servidor',
    'client': 'cliente',
    'code': 'codigo',
    'bug': 'error',
    'debug': 'depurar',
    'deploy': 'desplegar',
    'commit': 'guardar',
    'push': 'subir',
    'pull': 'bajar',
    'merge': 'fusionar',
    'branch': 'rama',
    'chat': 'chat',
    'message': 'mensaje',
    'call': 'llamada',
    'video': 'video',
    'audio': 'audio',
    'image': 'imagen',
    'text': 'texto',
    'link': 'enlace',
    'password': 'contrasena',
    'login': 'iniciar sesion',
    'logout': 'cerrar sesion',
    'settings': 'configuracion',
    'update': 'actualizar',
    'install': 'instalar',
    'delete': 'eliminar',
    'create': 'crear',
    'open': 'abrir',
    'close': 'cerrar',
    'save': 'guardar',
    'load': 'cargar',
    'start': 'iniciar',
    'stop': 'detener',
    'pause': 'pausar',
    'play': 'reproducir',
    'search': 'buscar',
    'find': 'encontrar',
    'replace': 'reemplazar',
    'copy': 'copiar',
    'paste': 'pegar',
    'cut': 'cortar',
    'undo': 'deshacer',
    'redo': 'rehacer',
}

# Contractions that sound better expanded for TTS clarity
CONTRACTIONS = {
    'al': 'a el',
    'del': 'de el',
}


def remove_accents(text: str) -> str:
    """Remove Spanish accents for better TTS clarity."""
    for accented, plain in ACCENT_MAP.items():
        text = text.replace(accented, plain)
    return text


def expand_numbers(text: str) -> str:
    """Convert numbers to words for better TTS pronunciation."""
    def _num_to_words(num_str):
        """Convert a numeric string to Spanish words."""
        if len(num_str) > 4:
            return num_str
        if '.' in num_str:
            return num_str
        if num_str.startswith('0') and len(num_str) > 1:
            return ' '.join(NUMBER_WORDS.get(c, c) for c in num_str)

        num = int(num_str)

        if num_str in NUMBER_WORDS:
            return NUMBER_WORDS[num_str]

        if 21 <= num <= 99:
            tens = (num // 10) * 10
            ones = num % 10
            if ones == 0:
                return NUMBER_WORDS.get(str(tens), num_str)
            connector = ' y ' if tens >= 30 else 'i'
            tens_word = NUMBER_WORDS.get(str(tens), str(tens))
            ones_word = NUMBER_WORDS.get(str(ones), str(ones))
            return f"{tens_word}{connector}{ones_word}"

        if 101 <= num <= 999:
            hundreds = num // 100
            remainder = num % 100
            hundred_words = {
                1: 'ciento', 2: 'doscientos', 3: 'trescientos',
                4: 'cuatrocientos', 5: 'quinientos', 6: 'seiscientos',
                7: 'setecientos', 8: 'ochocientos', 9: 'novecientos'
            }
            result = hundred_words.get(hundreds, f"{NUMBER_WORDS.get(str(hundreds), str(hundreds))}cientos")
            if remainder > 0:
                result += f" {_num_to_words(str(remainder))}"
            return result

        if 1000 <= num <= 9999:
            thousands = num // 1000
            remainder = num % 1000
            if thousands == 1:
                result = 'mil'
            else:
                result = f"{_num_to_words(str(thousands))} mil"
            if remainder > 0:
                result += f" {_num_to_words(str(remainder))}"
            return result

        return num_str

    def replace_number(match):
        return _num_to_words(match.group())

    # Match numbers at word boundaries, or before units (GB, MB, etc.)
    return re.sub(r'\b(\d{1,4})(?=\s|$|[a-zA-Z])', replace_number, text)


def expand_percentages(text: str) -> str:
    """Convert percentages to spoken form: 45% -> cuarenta y cinco por ciento."""
    def _pct_replace(match):
        num_str = match.group(1)
        words = _simple_num_to_words(num_str)
        return f"{words} por ciento"

    def _simple_num_to_words(num_str):
        """Simplified number to words for percentages."""
        if num_str in NUMBER_WORDS:
            return NUMBER_WORDS[num_str]
        try:
            num = int(num_str)
        except ValueError:
            return num_str

        if 21 <= num <= 99:
            tens = (num // 10) * 10
            ones = num % 10
            if ones == 0:
                return NUMBER_WORDS.get(str(tens), num_str)
            connector = ' y ' if tens >= 30 else 'i'
            tens_word = NUMBER_WORDS.get(str(tens), str(tens))
            ones_word = NUMBER_WORDS.get(str(ones), str(ones))
            return f"{tens_word}{connector}{ones_word}"
        return num_str

    return re.sub(r'(\d{1,3})%', _pct_replace, text)


def expand_time_formats(text: str) -> str:
    """Convert time formats to spoken form: 14:30 -> las dos y media / catorce treinta."""
    def _time_replace(match):
        hours = int(match.group(1))
        minutes = int(match.group(2))

        # Use 12h format for natural speech
        hour_12 = hours % 12
        if hour_12 == 0:
            hour_12 = 12

        hour_word = _simple_num_to_words(str(hour_12))

        if minutes == 0:
            return f"las {hour_word} en punto"
        elif minutes == 15:
            return f"las {hour_word} y cuarto"
        elif minutes == 30:
            return f"las {hour_word} y media"
        elif minutes == 45:
            next_hour = (hours + 1) % 24
            next_12 = next_hour % 12
            if next_12 == 0:
                next_12 = 12
            return f"las {_simple_num_to_words(str(next_12))} menos cuarto"
        else:
            min_word = _simple_num_to_words(str(minutes))
            return f"las {hour_word} y {min_word}"

    def _simple_num_to_words(num_str):
        """Simplified number to words."""
        if num_str in NUMBER_WORDS:
            return NUMBER_WORDS[num_str]
        try:
            num = int(num_str)
        except ValueError:
            return num_str
        if 21 <= num <= 99:
            tens = (num // 10) * 10
            ones = num % 10
            if ones == 0:
                return NUMBER_WORDS.get(str(tens), num_str)
            connector = ' y ' if tens >= 30 else 'i'
            tens_word = NUMBER_WORDS.get(str(tens), str(tens))
            ones_word = NUMBER_WORDS.get(str(ones), str(ones))
            return f"{tens_word}{connector}{ones_word}"
        return num_str

    # First handle "las HH:MM" pattern (most common in Spanish)
    result = re.sub(r'las (\d{1,2}):(\d{2})\b', lambda m: _time_replace(m), text)
    # Then handle standalone HH:MM (not preceded by "las ")
    result = re.sub(r'(?<!las )(\b\d{1,2}):(\d{2})\b', lambda m: _time_replace(m), result)
    return result


def expand_size_units(text: str) -> str:
    """Add space and expand size units: 120GB -> ciento veinte gigabytes."""
    for unit, expansion in SIZE_UNITS.items():
        # Match number directly attached to unit (no space)
        pattern = re.compile(r'(\d+)' + re.escape(unit), re.IGNORECASE)
        def _replace(m, exp=expansion):
            num_str = m.group(1)
            # Try to convert number
            try:
                num = int(num_str)
                if num <= 20:
                    num_word = NUMBER_WORDS.get(num_str, num_str)
                elif num <= 99:
                    tens = (num // 10) * 10
                    ones = num % 10
                    if ones == 0:
                        num_word = NUMBER_WORDS.get(str(tens), num_str)
                    else:
                        connector = ' y ' if tens >= 30 else 'i'
                        num_word = f"{NUMBER_WORDS.get(str(tens), str(tens))}{connector}{NUMBER_WORDS.get(str(ones), str(ones))}"
                elif num <= 999:
                    h = num // 100
                    r = num % 100
                    hw = {1:'ciento',2:'doscientos',3:'trescientos',4:'cuatrocientos',5:'quinientos',6:'seiscientos',7:'setecientos',8:'ochocientos',9:'novecientos'}
                    num_word = hw.get(h, num_str)
                    if r > 0:
                        num_word += f" {_simple_convert(r)}"
                else:
                    num_word = num_str
            except ValueError:
                num_word = num_str
            return f"{num_word} {exp}"
        text = pattern.sub(_replace, text)
    return text


def _simple_convert(num):
    """Simple number to words helper."""
    if num in [int(k) for k in NUMBER_WORDS]:
        return NUMBER_WORDS.get(str(num), str(num))
    if 21 <= num <= 99:
        tens = (num // 10) * 10
        ones = num % 10
        if ones == 0:
            return NUMBER_WORDS.get(str(tens), str(num))
        connector = ' y ' if tens >= 30 else 'i'
        return f"{NUMBER_WORDS.get(str(tens), str(tens))}{connector}{NUMBER_WORDS.get(str(ones), str(ones))}"
    return str(num)


def expand_file_extensions(text: str) -> str:
    """Expand file extensions: main.py -> main punto pi y."""
    for ext, pronunciation in FILE_EXTENSIONS.items():
        # Match word + extension at word boundary
        pattern = re.compile(r'(\w)' + re.escape(ext) + r'\b', re.IGNORECASE)
        text = pattern.sub(rf'\1 {pronunciation}', text)
    return text


def expand_tech_terms(text: str) -> str:
    """Expand technical abbreviations for better pronunciation."""
    for term, expansion in TECH_EXPANSIONS.items():
        # Case-insensitive replacement, word boundary aware
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        text = pattern.sub(expansion, text)
    return text


def expand_abbreviations(text: str) -> str:
    """Expand common abbreviations for clearer TTS pronunciation."""
    for abbr, expansion in ABBREVIATIONS.items():
        # Escape the abbreviation for regex
        escaped = re.escape(abbr)
        if abbr.endswith('.'):
            # Abbreviations ending with period: match at word boundary before the abbr
            # e.g., 'Dr.' matches 'Dr.' at word start
            pattern = re.compile(r'\b' + escaped)
        else:
            pattern = re.compile(r'\b' + escaped + r'\b')
        text = pattern.sub(expansion, text)
    return text


def expand_symbols(text: str) -> str:
    """Expand symbols that TTS would read poorly.
    Protects URLs, emails, and file paths from symbol expansion.
    """
    # Protect URLs, emails, and paths
    protected = {}
    counter = [0]

    def _protect(match):
        key = f'__SYM{counter[0]}__'
        protected[key] = match.group(0)
        counter[0] += 1
        return key

    # Protect URLs
    text = re.sub(r'https?://\S+', _protect, text)
    # Protect domain/path patterns (e.g., ejemplo.com/info)
    text = re.sub(r'\b[\w-]+\.[a-z]{2,}/\S+', _protect, text)
    # Protect emails
    text = re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', _protect, text)
    # Protect Windows paths
    text = re.sub(r'[A-Z]:\\[\S]+', _protect, text)

    # Sort by length descending so longer patterns match first (e.g., '>=' before '>')
    for symbol, expansion in sorted(SYMBOL_EXPANSIONS.items(), key=lambda x: -len(x[0])):
        text = text.replace(symbol, expansion)

    # Restore protected content
    for key, value in protected.items():
        text = text.replace(key, value)

    # Clean up multiple spaces
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def expand_decimal_numbers(text: str) -> str:
    """Convert decimal numbers to spoken form: 3.14 -> tres punto uno cuatro."""
    def _decimal_replace(match):
        integer_part = match.group(1)
        decimal_part = match.group(2)
        # Convert integer part
        try:
            int_val = int(integer_part)
            if int_val in [int(k) for k in NUMBER_WORDS]:
                int_word = NUMBER_WORDS.get(str(int_val), integer_part)
            elif int_val <= 99:
                tens = (int_val // 10) * 10
                ones = int_val % 10
                if ones == 0:
                    int_word = NUMBER_WORDS.get(str(tens), str(int_val))
                else:
                    connector = ' y ' if tens >= 30 else 'i'
                    int_word = f"{NUMBER_WORDS.get(str(tens), str(tens))}{connector}{NUMBER_WORDS.get(str(ones), str(ones))}"
            else:
                int_word = integer_part
        except ValueError:
            int_word = integer_part
        # Read decimal digits individually
        decimal_words = ' '.join(NUMBER_WORDS.get(d, d) for d in decimal_part)
        return f"{int_word} punto {decimal_words}"

    # Match decimal numbers (e.g., 3.14, 0.5, 100.25)
    return re.sub(r'(\d+)\.(\d+)', _decimal_replace, text)


def expand_file_urls(text: str) -> str:
    """Simplify URLs for speech: https://api.example.com -> api punto example punto com."""
    # Remove protocol
    text = re.sub(r'https?://', '', text)
    # Remove www.
    text = re.sub(r'www\.', '', text)
    # Remove trailing slashes
    text = re.sub(r'/+$', '', text)
    return text


def expand_english_words(text: str) -> str:
    """Convert common English words to phonetic Spanish equivalents.

    Only expands lowercase or mixed-case words. Properly capitalized words
    (like brand names: Code, Chrome, Discord) are left untouched.
    """
    words = text.split()
    result = []
    for word in words:
        clean = word.strip('.,;:!?()[]{}"\'-')
        prefix = word[:len(word) - len(clean)]
        suffix = word[len(clean):]

        # Skip if the word starts with uppercase (likely a proper noun/brand)
        if clean and clean[0].isupper():
            result.append(word)
            continue

        lower = clean.lower()
        if lower in ENGLISH_TO_SPANISH:
            result.append(prefix + ENGLISH_TO_SPANISH[lower] + suffix)
        else:
            result.append(word)
    return ' '.join(result)


def add_pauses(text: str) -> str:
    """Add natural pauses for better TTS rhythm.

    Replaces semicolons with period+space for a clearer pause,
    and ensures proper spacing after punctuation.
    """
    # Semicolons → period (stronger pause in TTS)
    text = text.replace(';', '. ')
    # Colon followed by text → period (pause before listing)
    text = re.sub(r':\s+', '. ', text)
    # Multiple spaces → single
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def normalize_repeated_chars(text: str) -> str:
    """Normalize repeated characters: noooo -> no, aaaa -> a.
    Voice clone handles these poorly, so normalize them.
    """
    # Reduce repeated letters to max 2 (preserves double letters like 'll', 'rr')
    text = re.sub(r'([a-zA-Z])\1{2,}', r'\1\1', text)
    # Normalize repeated punctuation
    text = re.sub(r'([.!?]){2,}', r'\1', text)
    return text


def soften_difficult_clusters(text: str) -> str:
    """Add subtle breaks in consonant clusters that TTS struggles with.
    
    Examples:
    - 'prompt' -> 'prompt' (leave common words)
    - 'strengths' -> 'strengths' (leave, rare in Spanish)
    - Focus on Spanish-specific problem clusters
    """
    # These patterns cause garbled output in voice clone:
    # - 'sc' before consonant: 'disc' -> leave as-is (common)
    # - 'str' in middle of word: 'construir' -> leave (natural)
    # - 'xn', 'xc' combinations
    # Most Spanish words are already phonetically clean.
    # Only handle specific known-problematic patterns:
    
    # 'ps' at start (psicologia -> sicologia for TTS)
    text = re.sub(r'\bps([aeiou])', r's\1', text, flags=re.IGNORECASE)
    # 'pn' at start (neumonia -> neumonia, already fine)
    
    # 'x' before consonant (extra -> ekstra for clearer TTS)
    text = re.sub(r'\bx([tc])', r'ek\1', text, flags=re.IGNORECASE)
    
    # 'cc' before consonant (accion -> aksion for clearer TTS)
    text = re.sub(r'cc([ei])', r'ks\1', text, flags=re.IGNORECASE)
    
    return text


def apply_phonetic_respelling(text: str) -> str:
    """Apply phonetic respelling for words that TTS consistently mispronounces.
    
    Only applies to lowercase words to preserve proper nouns.
    Uses word boundary matching to avoid partial replacements.
    """
    words = text.split()
    result = []
    for word in words:
        # Extract prefix/punctuation
        clean = word.strip('.,;:!?()[]{}\"\'-')
        prefix = word[:len(word) - len(clean)]
        suffix = word[len(clean):]
        
        # Skip capitalized words (likely proper nouns/brands)
        if clean and clean[0].isupper():
            result.append(word)
            continue
        
        lower = clean.lower()
        if lower in PHONETIC_RESPELLING:
            result.append(prefix + PHONETIC_RESPELLING[lower] + suffix)
        else:
            result.append(word)
    return ' '.join(result)


def apply_rhythm_breaks(text: str) -> str:
    """Insert micro-pauses at natural clause boundaries for better TTS rhythm.
    
    Voice clone produces more natural output when there are subtle pauses
    at conversational boundaries (after introductory phrases, before
    important information, etc.).
    """
    for pattern, replacement in RHYTHM_BREAKS.items():
        text = text.replace(pattern, replacement)
    
    # Add micro-pause after 'y' when connecting independent clauses
    # (only when 'y' is followed by a capital letter or common clause starter)
    text = re.sub(r'\bY\b(?=\s+[A-Z])', 'Y.', text)
    
    return text


def add_breathing_pauses(text: str, max_words_before_pause: int = 12) -> str:
    """Add breathing pauses for longer sentences.
    
    Voice clone produces clearer output when sentences have natural
    breathing points. Inserts a period at natural clause boundaries
    if the sentence is getting too long.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result = []
    
    for sentence in sentences:
        words = sentence.split()
        if len(words) <= max_words_before_pause:
            result.append(sentence)
            continue
        
        # Find natural break points (commas, conjunctions)
        parts = re.split(r'(,\s+|\s+y\s+|\s+pero\s+|\s+que\s+|\s+porque\s+)', sentence)
        current = []
        current_len = 0
        
        for part in parts:
            part_words = part.split()
            if current_len + len(part_words) > max_words_before_pause and current:
                result.append(' '.join(current).rstrip(',').strip())
                current = part_words
                current_len = len(part_words)
            else:
                current.extend(part_words)
                current_len += len(part_words)
        
        if current:
            result.append(' '.join(current).strip())
    
    # Join with space only — sentences already have ending punctuation
    return ' '.join(result)


def expand_contractions(text: str) -> str:
    """Expand Spanish contractions for clearer pronunciation."""
    for contraction, expansion in CONTRACTIONS.items():
        text = re.sub(r'\b' + contraction + r'\b', expansion, text, flags=re.IGNORECASE)
    return text


def _protect_urls_emails(text: str) -> tuple:
    """Replace URLs and emails with placeholders to protect them during splitting.
    Returns (modified_text, dict_of_replacements)."""
    replacements = {}
    counter = [0]

    def _make_placeholder(match):
        key = f'__PROT{counter[0]}__'
        replacements[key] = match.group(0)
        counter[0] += 1
        return key

    # Protect URLs
    text = re.sub(r'https?://\S+', _make_placeholder, text)
    # Protect emails
    text = re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', _make_placeholder, text)
    # Protect file paths (Windows and Unix)
    text = re.sub(r'[A-Z]:\\[\S]+', _make_placeholder, text)
    text = re.sub(r'/[\w/.-]+', _make_placeholder, text)
    return text, replacements


def _restore_protected(text: str, replacements: dict) -> str:
    """Restore protected placeholders back to original content."""
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def split_sentences(text: str, max_words: int = 10) -> List[str]:
    """Split text into short sentences for better voice clone quality.

    Improved: uses natural pause points (commas, semicolons) and
    respects sentence boundaries better. Protects URLs, emails, and
    file paths from being split.
    """
    # Protect URLs, emails, and paths from splitting
    protected_text, replacements = _protect_urls_emails(text)

    # First split by existing sentence boundaries
    raw_sentences = re.split(r'(?<=[.!?])\s+', protected_text)

    result = []
    for sentence in raw_sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        words = sentence.split()
        if len(words) <= max_words:
            result.append(_restore_protected(sentence, replacements))
        else:
            # Try to split at commas and semicolons first
            clauses = re.split(r'(?<=[,;])\s*', sentence)
            current = []
            for clause in clauses:
                clause_words = clause.split()
                if len(current) + len(clause_words) <= max_words:
                    current.extend(clause_words)
                else:
                    if current:
                        result.append(_restore_protected(' '.join(current), replacements))
                    # If a single clause is too long, split at word boundaries
                    if len(clause_words) > max_words:
                        for i in range(0, len(clause_words), max_words):
                            chunk = clause_words[i:i + max_words]
                            result.append(_restore_protected(' '.join(chunk), replacements))
                        current = []
                    else:
                        current = clause_words[:]

            if current:
                result.append(_restore_protected(' '.join(current), replacements))

    return result if result else [_restore_protected(protected_text, replacements)]


def clean_for_tts(text: str) -> str:
    """Clean text for TTS voice clone."""
    # Remove exclamation marks (cause garbled output)
    text = text.replace('!', '.')
    text = text.replace('¡', '')
    text = text.replace('¿', '')

    # Protect emails and URLs before cleaning special chars
    protected = {}
    counter = [0]

    def _protect(match):
        key = f'__CLN{counter[0]}__'
        protected[key] = match.group(0)
        counter[0] += 1
        return key

    text = re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', _protect, text)
    text = re.sub(r'https?://\S+', _protect, text)

    # Remove special characters that confuse TTS
    text = re.sub(r'[#@$%^&*+=\[\]{}|\\<>~`]', '', text)

    # Restore protected content
    for key, value in protected.items():
        text = text.replace(key, value)

    # Normalize multiple periods (from !→. conversion or ellipsis)
    text = re.sub(r'\.{2,}', '.', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Ensure sentence ends with period
    if text and text[-1] not in '.!?':
        text += '.'

    return text


def add_emphasis_markers(text: str) -> str:
    """V5: Add subtle emphasis hints for important words.
    
    NOTE: Disabled adding periods before emphasis words as they
    break mid-sentence flow and cause garbage voice clone output.
    The TTS engine handles emphasis naturally from context.
    """
    return text

def apply_sentence_prosody(text: str) -> str:
    """V5: Apply prosody hints based on sentence type.
    
    Only applies prosody markers at the START of sentences to avoid
    breaking mid-sentence flow.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        # Only mark questions if the sentence STARTS with a question word
        # and we haven't already added punctuation before it
        is_question = sentence.endswith('?')
        if is_question:
            # Add a subtle pause before the question word only at the very start
            for qword in ['quien', 'como', 'cuando', 'donde', 'por que', 'cual']:
                pattern = re.compile(r'^(' + qword + r')\b', re.IGNORECASE)
                sentence = pattern.sub(r'\1', sentence, count=1)
        result.append(sentence)
    return ' '.join(result)

def improve_natural_phrases(text: str) -> str:
    """V5: Improve common phrases for more natural TTS output."""
    text_lower = text.lower()
    for phrase, improved in NATURAL_PHRASES.items():
        if phrase in text_lower:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            text = pattern.sub(improved, text, count=1)
    return text

def add_prosody_pauses(text: str) -> str:
    """V5: Add intelligent pauses based on content analysis.
    
    NOTE: Disabled adding periods after warning/technical words
    as they break mid-sentence flow. The TTS engine handles
    emphasis naturally from context and punctuation.
    """
    return text

def optimize_for_voice_clone(
    text: str,
    remove_accent_chars: bool = True,
    max_sentence_words: int = 10,
    expand_nums: bool = True,
    expand_tech: bool = True,
    expand_eng: bool = True,
) -> str:
    """
    Full optimization pipeline for voice clone TTS.

    V5 pipeline order:
    1. Expand structured formats (%, time, units) before cleaning
    2. Expand abbreviations and URLs
    3. Expand symbols
    4. Clean special characters
    5. Expand numbers, tech terms, English words
    6. Apply phonetic respelling for problematic words
    7. Normalize repeated chars and difficult clusters
    8. Apply rhythm breaks for natural pauses
    9. V5: Add emphasis markers for important words
    10. V5: Apply sentence prosody (questions vs statements)
    11. V5: Improve natural phrases
    12. V5: Add prosody pauses based on content type
    13. Remove accents
    14. Add pauses and breathing points
    15. Split into short sentences
    """
    if not text or not text.strip():
        return text

    # Step 1: Expand structured formats
    if expand_nums:
        text = expand_percentages(text)
        text = expand_time_formats(text)
        text = expand_size_units(text)
        text = expand_decimal_numbers(text)

    # Step 2: Expand URLs, file extensions, abbreviations
    text = expand_file_urls(text)
    text = expand_file_extensions(text)
    text = expand_abbreviations(text)

    # Step 3: Expand symbols
    text = expand_symbols(text)

    # Step 4: Clean special characters
    text = clean_for_tts(text)

    # Step 5: Expand numbers, tech terms, English words
    if expand_nums:
        text = expand_numbers(text)
    if expand_tech:
        text = expand_tech_terms(text)
    if expand_eng:
        text = expand_english_words(text)

    # Step 6: Expand contractions
    text = expand_contractions(text)

    # Step 6.1: Phonetic respelling
    text = apply_phonetic_respelling(text)

    # Step 6.2: Normalize repeated chars
    text = normalize_repeated_chars(text)

    # Step 6.3: Soften difficult clusters
    text = soften_difficult_clusters(text)

    # Step 6.4: Rhythm breaks
    text = apply_rhythm_breaks(text)

    # Step 9: V5 - Emphasis markers
    text = add_emphasis_markers(text)

    # Step 10: V5 - Sentence prosody
    text = apply_sentence_prosody(text)

    # Step 11: V5 - Natural phrases
    text = improve_natural_phrases(text)

    # Step 12: V5 - Prosody pauses
    text = add_prosody_pauses(text)

    # Step 13: Remove accents
    if remove_accent_chars:
        text = remove_accents(text)

    # Step 14: Add natural pauses
    text = add_pauses(text)

    # Step 15: Split into short sentences
    sentences = split_sentences(text, max_sentence_words)

    # Rejoin with proper spacing
    result = ' '.join(sentences)

    # Add breathing pauses for long combined text
    result = add_breathing_pauses(result, max_words_before_pause=max_sentence_words + 2)

    return result


def get_pronunciation_tips(text: str) -> List[str]:
    """Analyze text and return pronunciation tips for voice clone."""
    tips = []

    # Check for numbers
    if re.search(r'\d', text):
        tips.append("Contains numbers - will be expanded to words")

    # Check for decimal numbers
    if re.search(r'\d+\.\d+', text):
        tips.append("Contains decimal numbers - will be read digit by digit")

    # Check for abbreviations
    for abbr in ABBREVIATIONS:
        if abbr in text:
            tips.append(f"Abbreviation '{abbr}' will be expanded to '{ABBREVIATIONS[abbr]}'")

    # Check for symbols
    symbols_found = [s for s in SYMBOL_EXPANSIONS if s in text]
    if symbols_found:
        tips.append(f"Symbols found: {', '.join(symbols_found[:5])} - will be expanded")

    # Check for tech terms
    for term in TECH_EXPANSIONS:
        if re.search(r'\b' + re.escape(term) + r'\b', text, re.IGNORECASE):
            tips.append(f"Tech term '{term}' will be expanded to '{TECH_EXPANSIONS[term]}'")

    # Check for English words
    words = text.lower().split()
    english_found = [w for w in words if w in ENGLISH_TO_SPANISH]
    if english_found:
        tips.append(f"English words found: {', '.join(english_found)} - will be converted")

    # Check for long sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    long_sentences = [s for s in sentences if len(s.split()) > 10]
    if long_sentences:
        tips.append(f"{len(long_sentences)} long sentence(s) will be split")

    # Check for accents
    if any(c in text for c in 'áéíóúüñÁÉÍÓÚÜÑ'):
        tips.append("Contains accents - will be removed for clarity")

    # Check for URLs
    if re.search(r'https?://', text):
        tips.append("Contains URL(s) - will be simplified for speech")

    return tips


# ── Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        "¡Hola Nicolás! ¿Cómo estás? Soy Luna, tu asistente personal con inteligencia artificial.",
        "Buenos días. Tienes 3 mensajes nuevos y 15 notificaciones pendientes.",
        "El uso de CPU está al 45% y la RAM al 72%. Tu disco SSD tiene 120GB libres.",
        "Abre VS Code y revisa el archivo main.py. Hay un bug en la línea 42.",
        "OK, voy a descargar la actualización. El URL del servidor es https://api.example.com.",
        "Tu PC tiene 16GB de RAM, un procesador Intel i7 y una GPU RTX 3080.",
    ]

    for text in test_cases:
        print(f"Original:    {text}")
        optimized = optimize_for_voice_clone(text)
        print(f"Optimized:   {optimized}")
        tips = get_pronunciation_tips(text)
        if tips:
            print(f"Tips:        {'; '.join(tips)}")
        print()
