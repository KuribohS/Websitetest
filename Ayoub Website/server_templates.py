# -*- coding: utf-8 -*-
import socket
import os
IP_ADDRESS = '127.0.0.1'
PORT = 8002
HTDOCS = './htdocs' # ohne Slash am Ende

if not os.path.isdir(HTDOCS):
  print(f"Das Verzeichnis {HTDOCS} existiert nicht.")
  print("Lege es an, es muss die HTML-Dateien und anderen Dateien Deiner Website enthalten.")

if os.path.isdir(HTDOCS) and not os.listdir(HTDOCS):
  print(f"Das Verzeichnis {HTDOCS} ist leer. Verschiebe die Dateien deiner Website dorthin.")


def create_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((IP_ADDRESS, PORT))
    s.listen()
    print("Server läuft auf http://{}:{}".format(IP_ADDRESS, PORT))
    return s


def wait_for_next_request(my_socket):
    conn, addr = my_socket.accept()
    conn.settimeout(1)
    # print("Neue Verbindung: " + str(addr))
    # Anfrage auslesen, bis ein doppelter Zeilenumbruch kommt.
    # Ein Zeilenumbruch ist hier (wie bei Windows) ein Carriage-Return-Zeichen (\r) 
    # gefolgt von einem Newline-Zeichen (\n)
    request = b''
    while True:
        try:
            buffer = conn.recv(1024)
        except socket.timeout:
            # Ein Timeout kommt sehr wahrscheinlich auch wegen Chrome,
            # wir setzen den Buffer dann auch auf leer und behandeln
            # das unten.
            buffer = b''
            
        # Chrome öffnet immer schon eine neue Verbindung auf Vorrat.
        # Damit es keinen Timeout gibt, schickt Chrome leere Pakete.
        # Das mögen wir nicht...
        if len(buffer)==0:
            conn.close()
            # print("Verdammter Chrome, hör auf, Verbindungen zu horten...")
            conn, addr = my_socket.accept()
            conn.settimeout(1)
            # print("Neue Verbindung: " + str(addr))
            continue
        request += buffer
        if request.endswith(b'\r\n\r\n'):
            break
    #dekodieren, damit wir einen String haben
    return conn, request.decode("utf-8")


# TEST_REQUEST_ROOT = '''GET / HTTP/1.1
# Host: localhost:{}
# User-Agent: wt/1.0
# Accept: */*
#
# '''.format(PORT)
#
# TEST_REQUEST_FILE = '''GET /test.html HTTP/1.1
# Host: localhost:{}
# User-Agent: wt/1.0
# Accept: */*
#
# '''.format(PORT)
#
# TEST_REQUEST_DIR = '''GET /img/ HTTP/1.1
# Host: localhost:{}
# User-Agent: wt/1.0
# Accept: */*
#
# '''.format(PORT)
#
# TEST_REQUEST_SUBDIR = '''GET /static/css/test.css HTTP/1.1
# Host: localhost:{}
# User-Agent: wt/1.0
# Accept: */*
#
# '''.format(PORT)
#
# TEST_REQUEST_BAD = '''GETMEOUTOFHERE / HTTP/1.1
#
# '''.format(PORT)

def is_valid_request(request):
    return request.startswith("GET ")


# print(is_valid_request(TEST_REQUEST_ROOT))
# print(is_valid_request(TEST_REQUEST_DIR))
# print(is_valid_request(TEST_REQUEST_FILE))
# print(is_valid_request(TEST_REQUEST_SUBDIR))
# print(is_valid_request(TEST_REQUEST_BAD))

def get_request_path(request):
    return request.split(" ")[1]


# print(get_request_path(TEST_REQUEST_ROOT))
# print(get_request_path(TEST_REQUEST_DIR))
# print(get_request_path(TEST_REQUEST_FILE))
# print(get_request_path(TEST_REQUEST_SUBDIR))

def is_valid_path(path):
    return os.path.exists(HTDOCS + path)

def is_file(path):
    return os.path.isfile(HTDOCS + path)
    
def is_dir(path):
    return os.path.isdir(HTDOCS + path)

def is_dir_with_index(path):
    return is_dir(path) and is_file(path + '/index.html')


def get_content(path, context={}):
    if is_dir_with_index(path):
        file_path = HTDOCS + path + "/index.html"
    else:
        file_path = HTDOCS + path
    if file_path.endswith('.html'):
        with open(file_path, 'r', encoding='utf-8') as myfile:
            content = render_template(myfile.read(), file_path, context)
            return content.encode("utf-8")
    else:
        with open(file_path, 'rb') as myfile:
            return myfile.read()


def render_template(content, file_path, context):
    rendered = ""
    for line in content.splitlines(True):
        if "{@" in line:
            incfile = line.replace("{@", "").replace("@}", "").strip()
            if not incfile.startswith("/"):
                incfile = os.path.dirname(file_path) + incfile
            print("Datei wird eingebunden: " + incfile)
            # Hier wird einfach wieder über get_content der neue Content geholt.
            # Dadurch können auch weitere Templates eingebunden werden.
            # Der Context wird einfach immer weiter gereicht, so dass alle
            # vorher gesetzten Werte zur Verfügung stehen.
            rendered += get_content(incfile, context).decode('utf-8')
        elif "{#" in line:
            start = line.index("{#")
            try:
                end = line.index("#}")
                marker = line[start:end+2]
                key = marker[2:-2].strip()
                if key in context:
                    rendered += line.replace(marker, str(context[key]))
                    print("Platzhalter {} ersetzt mit {}.".format(marker, str(context[key])))
                else:
                    rendered += line.replace(marker, "UNKNOWN_KEY: {}".format(key))
                    print("Platzhalter nicht bekannt! Vertippt? {}".format(marker))
            except:
                print("Fehler: #} fehlt!")
        elif "{=" in line:
            start = line.index("{=")
            try:
                end = line.index("=}")
                marker = line[start:end+2]
                vals = marker[2:-2].strip().split("##")
                for val in vals:
                    key, value = val.strip().split("=")
                    context[key.strip()] = value.strip()
                    print(f"Wert gesetzt für {key}: {value}")
            except:
                print("Fehler: =} fehlt!")
        else:
            rendered += line
    return rendered

def get_content_type(path):
    # Groß-/Kleinschreibung ignorieren
    l_path = path.lower()
    if is_dir_with_index(path) or l_path.endswith(".html"):
        return "text/html"
    if l_path.endswith(".css"):
        return "text/css"
    if l_path.endswith(".js"):
        return "text/javascript"
    if l_path.endswith(".jpg") or l_path.endswith(".jpeg"):
        return "image/jpeg"
    if l_path.endswith(".png"):
        return "image/png"
    if l_path.endswith(".gif"):
        return "image/gif"
    return "text/plain"


def create_response(code, content=None, content_type="text/plain"):
    '''
    Die Funktion erzeugt eine komplette HTTP Response mit dem gewünschten `code` und 
    dem `content`. Der Content kann auch leer sein, wenn ein Fehler (4xx Codes) 
    übermittelt werden soll. Der `content_type` kann gesetzt werden, ansonsten wird 
    "text/plain" gesendet, das ist praktisch zum Testen.
    '''
    
    # Die folgenden Codes werden unterstützt, mit passender Meldung für das Protokoll.
    code_msg = {
        200: b"Ok",
        400: b"Bad Request",
        404: b"Not Found",
        403: b"Forbidden",
    }
    
    # Wenn der Content noch nicht codiert wurde, dann codieren wir ihn in UTF-8
    if type(content) == str:
        content = content.encode('utf-8')
    
    # Der Beginn der Antwort:
    response = b"HTTP/1.1 " + str(code).encode('utf-8') + b" " + code_msg[code] + b"\r\n"

    # Wen wir Content haben, dann geben wir die Content-Length und den Content-Type mit aus.
    if content:
        response += b"Content-Length: " + str(len(content)).encode('utf-8') + b"\r\n"
        response += b"Content-Type: " + content_type.encode('utf-8') + b"\r\n"
    
    # Ende des Headers, eine leere Zeile:
    response += b"\r\n"
    
    # Wenn wir Content für den Body haben, dann wird er einfach angehängt. 
    if content:
        response += content
    return response


def send_response(conn, code, content=None, content_type="text/plain"):
    '''
    Komfortfunktion, um mit einem Befehl eine Response zu erzeugen und zu verschicken.
    '''
    conn.sendall(create_response(code, content, content_type))
    conn.shutdown(socket.SHUT_RDWR)
    conn.close()


# print(create_response(200, "Hello World"))

def start_server():
    s = create_socket()
    while True:
        conn, request = wait_for_next_request(s)
        if is_valid_request(request):
            path = get_request_path(request)
            print("Anfrage für: {}".format(path))
            if is_file(path) or is_dir_with_index(path):
                print("Alles ok, Datei geschickt!")
                content = get_content(path)
                send_response(conn, 200, content, get_content_type(path))
            elif is_dir(path):
                print(f"Das ist ein Verzeichnis ohne index.html: {HTDOCS}{path}.")
                send_response(conn, 403, "Verzeichnisse werden nicht angezeigt.")
            else:
                print(f"Datei nicht gefunden. Liegt sie wirklich unter {HTDOCS}{path}?")
                send_response(conn, 404, "Datei nicht gefunden")
        else:
            print("Kein gültiger Request: " + request)
            send_response(conn, 400, "Das ist kein HTTP!")


if __name__ == "__main__":
    start_server()
