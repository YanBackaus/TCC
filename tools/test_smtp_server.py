import argparse
import json
import socketserver
import threading
import time
from datetime import datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path
from uuid import uuid4

from flask import Flask, abort, redirect, render_template_string, request, url_for


LAYOUT_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        :root {
            --bg: #f4f1ea;
            --card: rgba(255, 255, 255, 0.96);
            --text: #1f1f1f;
            --muted: #5f5a52;
            --line: #d9d3c7;
            --brand: #f0a500;
            --brand-dark: #111111;
            --danger: #bb2d3b;
            --shadow: 0 1rem 2.5rem rgba(17, 17, 17, 0.08);
            --radius: 18px;
            --font: "Segoe UI", Arial, sans-serif;
        }

        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: var(--font);
            color: var(--text);
            background:
                radial-gradient(circle at top, rgba(240, 165, 0, 0.18), transparent 30%),
                linear-gradient(180deg, #fbfaf7 0%, var(--bg) 100%);
        }

        a { color: inherit; text-decoration: none; }
        .shell { max-width: 1320px; margin: 0 auto; padding: 24px; }
        .hero {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 20px;
            padding: 24px;
            background: linear-gradient(135deg, #111111 0%, #1f1f1f 100%);
            color: white;
            border-radius: 24px;
            box-shadow: var(--shadow);
        }

        .hero h1 { margin: 0 0 8px; font-size: 2rem; }
        .hero p { margin: 0; color: rgba(255,255,255,0.78); }
        .hero-meta {
            display: grid;
            gap: 10px;
            align-content: start;
            min-width: 260px;
        }

        .pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 14px;
            border-radius: 999px;
            background: rgba(255,255,255,0.08);
            font-size: 0.95rem;
        }

        .grid {
            display: grid;
            grid-template-columns: 320px minmax(0, 1fr);
            gap: 20px;
        }

        .card {
            background: var(--card);
            border: 1px solid rgba(217, 211, 199, 0.9);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 20px;
        }

        .card h2, .card h3 { margin: 0 0 10px; }
        .card p { margin: 0 0 14px; color: var(--muted); }

        .stack { display: grid; gap: 14px; }
        .field { display: grid; gap: 8px; }
        .field label { font-weight: 600; }
        .field input, .field textarea, .field select {
            width: 100%;
            min-height: 46px;
            padding: 12px 14px;
            border: 1px solid var(--line);
            border-radius: 14px;
            font: inherit;
            background: white;
        }

        .field textarea {
            min-height: 240px;
            resize: vertical;
            font-family: "Courier New", monospace;
        }

        .row { display: flex; gap: 10px; flex-wrap: wrap; }
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            min-height: 46px;
            padding: 0 16px;
            border-radius: 999px;
            border: 1px solid var(--brand-dark);
            background: var(--brand);
            color: var(--brand-dark);
            font-weight: 700;
            cursor: pointer;
        }

        .btn:hover { background: var(--brand-dark); color: var(--brand); }
        .btn-secondary {
            background: transparent;
            border-color: var(--line);
            color: var(--text);
        }

        .btn-danger {
            background: transparent;
            color: var(--danger);
            border-color: rgba(187, 45, 59, 0.25);
        }

        .list {
            display: grid;
            gap: 10px;
        }

        .list-item {
            display: grid;
            gap: 6px;
            padding: 14px;
            border: 1px solid rgba(217, 211, 199, 0.9);
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.88);
        }

        .list-item.active {
            background: linear-gradient(135deg, rgba(240, 165, 0, 0.18), rgba(255,255,255,0.95));
            border-color: rgba(240, 165, 0, 0.45);
        }

        .muted { color: var(--muted); }
        .count { font-size: 0.9rem; color: var(--muted); }
        .section-title {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 14px;
        }

        .flash {
            margin-bottom: 16px;
            padding: 12px 14px;
            border-radius: 14px;
            border: 1px solid rgba(240, 165, 0, 0.25);
            background: rgba(240, 165, 0, 0.12);
        }

        .empty {
            padding: 18px;
            border-radius: 16px;
            background: rgba(244, 241, 234, 0.7);
            color: var(--muted);
        }

        .meta-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-bottom: 18px;
        }

        .meta-grid div {
            padding: 12px 14px;
            border-radius: 14px;
            background: rgba(244, 241, 234, 0.7);
            border: 1px solid rgba(217, 211, 199, 0.9);
        }

        .tag {
            display: inline-flex;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(17,17,17,0.08);
            font-size: 0.85rem;
        }

        @media (max-width: 980px) {
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="shell">
        <section class="hero">
            <div>
                <h1>Gerenciador de E-mails de Teste</h1>
                <p>Servidor SMTP local e caixa de entrada web para acelerar seus testes.</p>
            </div>
            <div class="hero-meta">
                <div class="pill">SMTP: {{ smtp_host }}:{{ smtp_port }}</div>
                <div class="pill">Web: http://{{ web_host }}:{{ web_port }}</div>
                <div class="pill">Inbox: {{ inbox_dir }}</div>
            </div>
        </section>

        {% if flash_message %}
        <div class="flash">{{ flash_message }}</div>
        {% endif %}

        {{ body|safe }}
    </div>
</body>
</html>
"""


HOME_TEMPLATE = """
<div class="grid">
    <aside class="stack">
        <section class="card">
            <div class="section-title">
                <div>
                    <h2>Contas falsas</h2>
                    <p>Crie e-mails locais para usar nos testes.</p>
                </div>
            </div>

            <form class="stack" method="POST" action="{{ url_for('create_account') }}">
                <div class="field">
                    <label for="local_part">Nome do e-mail</label>
                    <input id="local_part" name="local_part" type="text" placeholder="ex.: almoxarife">
                </div>
                <div class="field">
                    <label for="domain">Dominio</label>
                    <input id="domain" name="domain" type="text" value="{{ default_domain }}" placeholder="teste.local">
                </div>
                <button class="btn" type="submit">Criar e-mail de teste</button>
            </form>
        </section>

        <section class="card">
            <div class="section-title">
                <div>
                    <h2>Enderecos cadastrados</h2>
                    <p>{{ accounts|length }} conta(s) criada(s).</p>
                </div>
                {% if selected_account %}
                <a class="btn btn-secondary" href="{{ url_for('home') }}">Ver tudo</a>
                {% endif %}
            </div>

            <div class="list">
                {% for account in accounts %}
                <div class="list-item {% if selected_account == account.address %}active{% endif %}">
                    <a href="{{ url_for('home', account=account.address) }}">
                        <strong>{{ account.address }}</strong>
                    </a>
                    <span class="count">{{ account.message_count }} mensagem(ns)</span>
                    <span class="muted">Criado em {{ account.created_at }}</span>
                    <form method="POST" action="{{ url_for('delete_account', address=account.address) }}">
                        <button class="btn btn-danger" type="submit">Remover conta</button>
                    </form>
                </div>
                {% else %}
                <div class="empty">Nenhuma conta criada ainda.</div>
                {% endfor %}
            </div>
        </section>
    </aside>

    <main class="stack">
        <section class="card">
            <div class="section-title">
                <div>
                    <h2>{{ 'Inbox de ' + selected_account if selected_account else 'Todos os e-mails recebidos' }}</h2>
                    <p>{{ emails|length }} mensagem(ns) encontrada(s).</p>
                </div>
            </div>

            <div class="list">
                {% for email in emails %}
                <a class="list-item {% if selected_email and selected_email.filename == email.filename %}active{% endif %}"
                   href="{{ url_for('view_email', filename=email.filename, account=selected_account) }}">
                    <strong>{{ email.subject }}</strong>
                    <span class="muted">{{ email.from }} -> {{ email.to }}</span>
                    <span class="count">{{ email.received_at }}</span>
                    <span>{{ email.preview or 'Sem conteudo de texto.' }}</span>
                    {% if email.primary_link %}
                    <span class="tag">Com link detectado</span>
                    {% endif %}
                </a>
                {% else %}
                <div class="empty">Nenhum e-mail recebido ainda. Deixe o SMTP rodando e envie uma mensagem para uma das contas de teste.</div>
                {% endfor %}
            </div>
        </section>

        <section class="card">
            {% if selected_email %}
            <div class="section-title">
                <div>
                    <h2>{{ selected_email.subject }}</h2>
                    <p>Arquivo: {{ selected_email.filename }}</p>
                </div>
            </div>

            {% if selected_email.links %}
            <div class="row" style="margin-bottom: 14px;">
                {% for link in selected_email.links %}
                <a class="btn" href="{{ link }}" target="_blank" rel="noopener noreferrer">Abrir link detectado</a>
                {% endfor %}
            </div>
            {% endif %}

            <div class="meta-grid">
                <div><strong>De:</strong><br><span class="muted">{{ selected_email.from or 'Nao informado' }}</span></div>
                <div><strong>Para:</strong><br><span class="muted">{{ selected_email.to or 'Nao informado' }}</span></div>
                <div><strong>Recebido em:</strong><br><span class="muted">{{ selected_email.received_at }}</span></div>
            </div>

            <div class="field">
                <label>Mensagem</label>
                <textarea readonly>{{ selected_email.body }}</textarea>
            </div>

            <div class="field">
                <label>Conteudo bruto</label>
                <textarea readonly>{{ selected_email.raw }}</textarea>
            </div>
            {% else %}
            <h2>Selecione um e-mail</h2>
            <p>Escolha uma mensagem na lista para abrir o conteudo completo e os links detectados.</p>
            {% endif %}
        </section>
    </main>
</div>
"""


URL_PATTERN = __import__("re").compile(r"https?://[^\s<>\"]+")


class ThreadedSMTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, handler_class, output_dir):
        super().__init__(server_address, handler_class)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_message(self, mail_from, rcpt_to, data_lines):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}-{uuid4().hex[:8]}.eml"
        target = self.output_dir / filename
        headers = [
            f"X-Test-SMTP-From: {mail_from}",
            f"X-Test-SMTP-To: {', '.join(rcpt_to)}",
            f"X-Test-SMTP-Received-At: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        ]
        content = "\n".join(headers + [""] + data_lines).strip() + "\n"
        target.write_text(content, encoding="utf-8")
        print(f"[SMTP] Mensagem salva em: {target}")
        return target


class SMTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.mail_from = ""
        self.rcpt_to = []
        self.data_lines = []
        self.in_data = False
        self._send_line("220 Test SMTP Server Ready")

        while True:
            raw_line = self.rfile.readline()
            if not raw_line:
                break

            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")

            if self.in_data:
                if line == ".":
                    saved = self.server.save_message(self.mail_from, self.rcpt_to, self.data_lines)
                    self._reset_message()
                    self._send_line(f"250 Message accepted as {saved.name}")
                    continue

                if line.startswith(".."):
                    line = line[1:]
                self.data_lines.append(line)
                continue

            command = line.upper()

            if command.startswith("EHLO") or command.startswith("HELO"):
                self.wfile.write(b"250-localhost\r\n")
                self.wfile.write(b"250 SIZE 10485760\r\n")
            elif command.startswith("MAIL FROM:"):
                self.mail_from = line[10:].strip()
                self._send_line("250 OK")
            elif command.startswith("RCPT TO:"):
                self.rcpt_to.append(line[8:].strip())
                self._send_line("250 OK")
            elif command == "DATA":
                if not self.rcpt_to:
                    self._send_line("503 Bad sequence of commands")
                else:
                    self.in_data = True
                    self._send_line("354 End data with <CR><LF>.<CR><LF>")
            elif command == "RSET":
                self._reset_message()
                self._send_line("250 OK")
            elif command == "NOOP":
                self._send_line("250 OK")
            elif command == "QUIT":
                self._send_line("221 Bye")
                break
            elif command.startswith("AUTH"):
                self._send_line("502 AUTH not supported by test server")
            elif command == "STARTTLS":
                self._send_line("454 TLS not available on test server")
            else:
                self._send_line("502 Command not implemented")

    def _reset_message(self):
        self.mail_from = ""
        self.rcpt_to = []
        self.data_lines = []
        self.in_data = False

    def _send_line(self, message):
        self.wfile.write(f"{message}\r\n".encode("utf-8"))


class TestSMTPServer:
    def __init__(self, host="127.0.0.1", port=1025, output_dir=".smtp-test-inbox"):
        self.host = host
        self.port = port
        self.output_dir = Path(output_dir)
        self._server = ThreadedSMTPServer((host, port), SMTPHandler, self.output_dir)
        self._thread = None

    def serve_forever(self):
        print(f"[SMTP] Servidor de teste ativo em smtp://{self.host}:{self.port}")
        print(f"[SMTP] Emails serao salvos em: {self.output_dir.resolve()}")
        self._server.serve_forever()

    def start_in_thread(self):
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._thread.start()
        return self._thread

    def shutdown(self):
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=1)


class FakeAccountStore:
    def __init__(self, accounts_file):
        self.accounts_file = Path(accounts_file)
        self.accounts_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self):
        if not self.accounts_file.exists():
            return []
        try:
            return json.loads(self.accounts_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _save(self, accounts):
        self.accounts_file.write_text(
            json.dumps(accounts, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def list_accounts(self):
        accounts = self._load()
        return sorted(accounts, key=lambda item: item["address"].lower())

    def create_account(self, local_part, domain):
        local_part = local_part.strip().lower()
        domain = domain.strip().lower()

        if not local_part:
            raise ValueError("Informe o nome do e-mail.")
        if not domain:
            raise ValueError("Informe o dominio do e-mail.")

        address = f"{local_part}@{domain}"
        accounts = self._load()
        if any(item["address"] == address for item in accounts):
            raise ValueError("Esse e-mail de teste ja existe.")

        accounts.append(
            {
                "address": address,
                "created_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            }
        )
        self._save(accounts)
        return address

    def delete_account(self, address):
        accounts = self._load()
        accounts = [item for item in accounts if item["address"] != address]
        self._save(accounts)


class InboxReader:
    def __init__(self, inbox_dir):
        self.inbox_dir = Path(inbox_dir)
        self.inbox_dir.mkdir(parents=True, exist_ok=True)

    def _split_saved_email(self, target_path):
        raw_bytes = target_path.read_bytes()
        for marker in (b"\r\n\r\n", b"\n\n"):
            separator_index = raw_bytes.find(marker)
            if separator_index != -1:
                return raw_bytes[:separator_index], raw_bytes[separator_index + len(marker):]
        return raw_bytes, b""

    def _parse_test_metadata(self, metadata_text):
        metadata = {}
        for line in metadata_text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
        return metadata

    def _read_email_file(self, target_path):
        _, message_bytes = self._split_saved_email(target_path)
        return BytesParser(policy=policy.default).parsebytes(message_bytes)

    def _extract_text(self, message):
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/plain" and not part.get_filename():
                    return part.get_content().strip()
            return ""
        return message.get_content().strip()

    def _extract_html(self, message):
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/html" and not part.get_filename():
                    return part.get_content().strip()
            return ""
        if message.get_content_type() == "text/html":
            return message.get_content().strip()
        return ""

    def _extract_links(self, *contents):
        links = []
        for content in contents:
            if not content:
                continue
            for link in URL_PATTERN.findall(content):
                if link not in links:
                    links.append(link)
        return links

    def _build_summary(self, target_path):
        metadata_bytes, _ = self._split_saved_email(target_path)
        metadata = self._parse_test_metadata(metadata_bytes.decode("utf-8", errors="replace"))
        message = self._read_email_file(target_path)
        body = self._extract_text(message)
        html_body = self._extract_html(message)
        links = self._extract_links(body, html_body)
        preview = body.replace("\n", " ").strip()
        return {
            "filename": target_path.name,
            "subject": message.get("Subject", "(Sem assunto)"),
            "from": message.get("From", ""),
            "to": message.get("To", metadata.get("X-Test-SMTP-To", "")),
            "received_at": metadata.get("X-Test-SMTP-Received-At", ""),
            "preview": preview[:180] + ("..." if len(preview) > 180 else ""),
            "primary_link": links[0] if links else "",
            "modified_at": target_path.stat().st_mtime,
        }

    def list_emails(self, account=None):
        emails = []
        for path in self.inbox_dir.glob("*.eml"):
            if not path.is_file():
                continue
            summary = self._build_summary(path)
            if account and account.lower() not in summary["to"].lower():
                continue
            emails.append(summary)
        return sorted(emails, key=lambda item: item["modified_at"], reverse=True)

    def get_email(self, filename):
        safe_name = Path(filename).name
        if safe_name != filename:
            raise ValueError("Nome de arquivo invalido.")

        target_path = self.inbox_dir / safe_name
        if not target_path.exists() or not target_path.is_file():
            return None

        metadata_bytes, _ = self._split_saved_email(target_path)
        metadata = self._parse_test_metadata(metadata_bytes.decode("utf-8", errors="replace"))
        message = self._read_email_file(target_path)
        body = self._extract_text(message)
        html_body = self._extract_html(message)
        return {
            "filename": target_path.name,
            "subject": message.get("Subject", "(Sem assunto)"),
            "from": message.get("From", ""),
            "to": message.get("To", metadata.get("X-Test-SMTP-To", "")),
            "received_at": metadata.get("X-Test-SMTP-Received-At", ""),
            "body": body,
            "html_body": html_body,
            "links": self._extract_links(body, html_body),
            "raw": target_path.read_text(encoding="utf-8", errors="replace"),
        }


class TestMailManager:
    def __init__(
        self,
        smtp_host="127.0.0.1",
        smtp_port=1025,
        web_host="127.0.0.1",
        web_port=8025,
        output_dir=".smtp-test-inbox",
        accounts_file=".smtp-test-accounts.json",
        default_domain="teste.local",
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.web_host = web_host
        self.web_port = web_port
        self.output_dir = Path(output_dir)
        self.accounts_store = FakeAccountStore(accounts_file)
        self.inbox_reader = InboxReader(self.output_dir)
        self.default_domain = default_domain
        self.flash_message = ""

        self.smtp_server = TestSMTPServer(smtp_host, smtp_port, output_dir)
        self.app = Flask(__name__)
        self._register_routes()

    def _register_routes(self):
        @self.app.route("/", methods=["GET"])
        def home():
            selected_account = request.args.get("account", "").strip() or None
            selected_filename = request.args.get("email", "").strip() or None
            emails = self.inbox_reader.list_emails(account=selected_account)
            selected_email = None
            if selected_filename:
                selected_email = self.inbox_reader.get_email(selected_filename)
                if selected_email is None:
                    abort(404)

            accounts = []
            message_count_map = {}
            for email in self.inbox_reader.list_emails():
                recipients = [item.strip().strip("<>") for item in email["to"].split(",") if item.strip()]
                for recipient in recipients:
                    message_count_map[recipient.lower()] = message_count_map.get(recipient.lower(), 0) + 1

            for account in self.accounts_store.list_accounts():
                accounts.append(
                    {
                        **account,
                        "message_count": message_count_map.get(account["address"].lower(), 0),
                    }
                )

            body = render_template_string(
                HOME_TEMPLATE,
                accounts=accounts,
                emails=emails,
                selected_email=selected_email,
                selected_account=selected_account,
                default_domain=self.default_domain,
            )
            flash_message = self.flash_message
            self.flash_message = ""
            return render_template_string(
                LAYOUT_TEMPLATE,
                title="Gerenciador de E-mails de Teste",
                body=body,
                flash_message=flash_message,
                smtp_host=self.smtp_host,
                smtp_port=self.smtp_port,
                web_host=self.web_host,
                web_port=self.web_port,
                inbox_dir=self.output_dir.resolve(),
            )

        @self.app.route("/accounts", methods=["POST"])
        def create_account():
            try:
                address = self.accounts_store.create_account(
                    request.form.get("local_part", ""),
                    request.form.get("domain", self.default_domain),
                )
                self.flash_message = f"E-mail de teste criado: {address}"
            except ValueError as error:
                self.flash_message = str(error)
            return redirect(url_for("home"))

        @self.app.route("/accounts/<path:address>/delete", methods=["POST"])
        def delete_account(address):
            self.accounts_store.delete_account(address)
            self.flash_message = f"E-mail removido: {address}"
            return redirect(url_for("home"))

        @self.app.route("/emails/<path:filename>", methods=["GET"])
        def view_email(filename):
            account = request.args.get("account", "").strip()
            return redirect(url_for("home", account=account or None, email=filename))

    def serve_forever(self):
        self.smtp_server.start_in_thread()
        time.sleep(0.2)
        print(f"[MAIL] Interface web ativa em http://{self.web_host}:{self.web_port}")
        print(f"[MAIL] Crie e-mails falsos e acompanhe as mensagens sem login no sistema principal.")
        self.app.run(host=self.web_host, port=self.web_port, debug=False, use_reloader=False)

    def shutdown(self):
        self.smtp_server.shutdown()


def parse_args():
    parser = argparse.ArgumentParser(description="Servidor SMTP local com gerenciador web de e-mails de teste.")
    parser.add_argument("--host", default="127.0.0.1", help="Host para escutar no SMTP.")
    parser.add_argument("--port", type=int, default=1025, help="Porta SMTP de teste.")
    parser.add_argument("--web-host", default="127.0.0.1", help="Host da interface web.")
    parser.add_argument("--web-port", type=int, default=8025, help="Porta da interface web.")
    parser.add_argument(
        "--output-dir",
        default=".smtp-test-inbox",
        help="Pasta onde os emails .eml serao salvos.",
    )
    parser.add_argument(
        "--accounts-file",
        default=".smtp-test-accounts.json",
        help="Arquivo JSON com as contas falsas cadastradas.",
    )
    parser.add_argument(
        "--default-domain",
        default="teste.local",
        help="Dominio padrao usado ao criar e-mails falsos.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    manager = TestMailManager(
        smtp_host=args.host,
        smtp_port=args.port,
        web_host=args.web_host,
        web_port=args.web_port,
        output_dir=args.output_dir,
        accounts_file=args.accounts_file,
        default_domain=args.default_domain,
    )
    try:
        manager.serve_forever()
    except KeyboardInterrupt:
        print("\n[MAIL] Servidor encerrado.")
    finally:
        manager.shutdown()


if __name__ == "__main__":
    main()
