"""Envio do e-mail pelo SMTP do Gmail (SSL, porta 465) com senha de app."""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

SERVIDOR_PADRAO = "smtp.gmail.com"
PORTA_PADRAO = 465


def montar_mensagem(remetente, destino, assunto, texto, html, csv_bytes=None, nome_csv="vagas.csv"):
    mensagem = MIMEMultipart("mixed")
    mensagem["Subject"] = assunto
    mensagem["From"] = remetente
    mensagem["To"] = destino
    mensagem["Date"] = formatdate(localtime=False)
    mensagem["Message-ID"] = make_msgid(domain="reid.local")
    corpo = MIMEMultipart("alternative")
    corpo.attach(MIMEText(texto, "plain", "utf-8"))
    corpo.attach(MIMEText(html, "html", "utf-8"))
    mensagem.attach(corpo)
    if csv_bytes:
        anexo = MIMEApplication(csv_bytes, _subtype="csv")
        anexo.add_header("Content-Disposition", "attachment", filename=nome_csv)
        mensagem.attach(anexo)
    return mensagem


def enviar(mensagem, remetente, senha, servidor=SERVIDOR_PADRAO, porta=PORTA_PADRAO):
    with smtplib.SMTP_SSL(servidor, porta, timeout=60) as smtp:
        smtp.login(remetente, senha)
        smtp.send_message(mensagem)
