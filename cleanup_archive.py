#!/usr/bin/env python3
"""
IOB — Limpeza do Arquivo Morto de Análises de Fornecedores
Exclui permanentemente arquivos arquivados há mais de 365 dias.
Executado diariamente via cron: /etc/cron.d/iob-archive-cleanup
"""
import os, json, logging
from datetime import datetime, timezone, timedelta

ARCHIVE_DIR   = '/var/www/iob-fornecedores/arquivo-morto'
MANIFEST_PATH = os.path.join(ARCHIVE_DIR, '.manifest.json')
RETENTION_DAYS = 365
LOG_FILE       = '/var/log/iob-archive-cleanup.log'

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S',
)
log = logging.getLogger(__name__)


def load_manifest():
    if not os.path.isfile(MANIFEST_PATH):
        return {}
    with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_manifest(data):
    with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run():
    if not os.path.isdir(ARCHIVE_DIR):
        log.info('Pasta de arquivo morto não existe — nada a fazer.')
        return

    manifest = load_manifest()
    cutoff   = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    deleted  = []
    kept     = []

    for filename, archived_at_str in list(manifest.items()):
        filepath = os.path.join(ARCHIVE_DIR, filename)

        if not os.path.isfile(filepath):
            log.warning('Arquivo no manifesto não encontrado no disco: %s — removendo do manifesto.', filename)
            del manifest[filename]
            continue

        try:
            archived_at = datetime.fromisoformat(archived_at_str)
            # Garante timezone-aware para comparação
            if archived_at.tzinfo is None:
                archived_at = archived_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            log.error('Data inválida no manifesto para %s: %r — ignorando.', filename, archived_at_str)
            kept.append(filename)
            continue

        age_days = (datetime.now(timezone.utc) - archived_at).days

        if archived_at <= cutoff:
            try:
                os.remove(filepath)
                del manifest[filename]
                deleted.append(filename)
                log.info('EXCLUÍDO (%.0f dias): %s', age_days, filename)
            except OSError as e:
                log.error('Falha ao excluir %s: %s', filename, e)
                kept.append(filename)
        else:
            days_left = RETENTION_DAYS - age_days
            log.debug('Mantido (%d dias restantes): %s', days_left, filename)
            kept.append(filename)

    save_manifest(manifest)
    log.info('Concluído — excluídos: %d | mantidos: %d', len(deleted), len(kept))


if __name__ == '__main__':
    run()
