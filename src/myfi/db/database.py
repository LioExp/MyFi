import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class Database:
    """Gerente central da base de dados SQLite do MyFi."""

    def __init__(self, db_path: str = None):
        """
        Inicializa a ligação à base de dados.

        Args:
            db_path: Caminho para o ficheiro SQLite. Se None, usa 'data/myfi.db' no projeto.
        """
        if db_path is None:
            # Obtém a raiz do projeto (assumindo que este ficheiro está em src/myfi/db/)
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            db_dir = project_root / 'data'
            db_dir.mkdir(exist_ok=True)
            db_path = db_dir / 'myfi.db'

        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")  # Melhor concorrência
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()
        self._init_tables()

    def _init_tables(self):
        """Cria as tabelas se não existirem."""
        # Tabela de dispositivos (descobertos pelo scanner)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                mac TEXT PRIMARY KEY,
                hostname TEXT,
                ip TEXT,
                first_seen TEXT,
                last_seen TEXT,
                interface TEXT
            )
        ''')

        # Tabela de logs de tráfego (cada medição do monitor)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS traffic_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT NOT NULL,
                bytes_sent INTEGER DEFAULT 0,
                bytes_recv INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (mac) REFERENCES devices(mac)
            )
        ''')

        # Tabela de limites de consumo
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT NOT NULL,
                limit_type TEXT NOT NULL DEFAULT 'daily',  -- daily, weekly, monthly, custom
                bytes_max INTEGER NOT NULL,
                active INTEGER DEFAULT 1,
                FOREIGN KEY (mac) REFERENCES devices(mac)
            )
        ''')

        # Tabela de histórico de alertas
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                mac TEXT,
                alert_type TEXT NOT NULL,  -- warning, critical, info
                message TEXT NOT NULL,
                channel TEXT DEFAULT 'telegram',
                success INTEGER DEFAULT 1,
                FOREIGN KEY (mac) REFERENCES devices(mac)
            )
        ''')

        # Tabela de alertas pendentes (para retry)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                mac TEXT,
                alert_type TEXT NOT NULL,
                message TEXT NOT NULL,
                channel TEXT DEFAULT 'telegram',
                attempts INTEGER DEFAULT 0,
                last_attempt TEXT,
                status TEXT DEFAULT 'pending'
            )
        ''')

        # Índices para consultas frequentes
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_traffic_mac_timestamp
            ON traffic_logs (mac, timestamp)
        ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp
            ON alerts_log (timestamp)
        ''')

        self.conn.commit()
        logger.debug("Tabelas da base de dados inicializadas.")

    # ---------- Métodos para Devices ----------

    def save_device(self, mac: str, hostname: str, ip: str, interface: str = "N/A"):
        """
        Insere ou atualiza um dispositivo na tabela devices.
        Usa UPSERT para atualizar last_seen e ip se o MAC já existir.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO devices (mac, hostname, ip, first_seen, last_seen, interface)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(mac) DO UPDATE SET
                hostname = excluded.hostname,
                ip = excluded.ip,
                last_seen = excluded.last_seen,
                interface = excluded.interface
        ''', (mac, hostname, ip, now, now, interface))
        self.conn.commit()
        logger.debug(f"Dispositivo guardado: {mac} ({hostname})")

    def get_device(self, mac: str) -> dict | None:
        """Retorna um dispositivo pelo MAC."""
        self.cursor.execute('SELECT * FROM devices WHERE mac = ?', (mac,))
        row = self.cursor.fetchone()
        if row:
            return dict(zip(['mac', 'hostname', 'ip', 'first_seen', 'last_seen', 'interface'], row))
        return None

    def get_all_devices(self) -> list[dict]:
        """Retorna todos os dispositivos registados."""
        self.cursor.execute('SELECT * FROM devices ORDER BY last_seen DESC')
        rows = self.cursor.fetchall()
        columns = ['mac', 'hostname', 'ip', 'first_seen', 'last_seen', 'interface']
        return [dict(zip(columns, row)) for row in rows]

    # ---------- Métodos para Traffic Logs ----------

    def save_traffic(self, mac: str, bytes_sent: int, bytes_recv: int, timestamp: str = None):
        """Regista uma medição de tráfego."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO traffic_logs (mac, bytes_sent, bytes_recv, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (mac, bytes_sent, bytes_recv, timestamp))
        self.conn.commit()
        logger.debug(f"Tráfego guardado: {mac} | ↑{bytes_sent} ↓{bytes_recv}")

    def get_traffic_summary(self, mac: str, since: str = None) -> dict:
        """
        Retorna o tráfego total (bytes enviados/recebidos) para um MAC desde uma data.
        Se since for None, retorna o total de sempre.
        """
        if since:
            self.cursor.execute('''
                SELECT SUM(bytes_sent), SUM(bytes_recv)
                FROM traffic_logs
                WHERE mac = ? AND timestamp >= ?
            ''', (mac, since))
        else:
            self.cursor.execute('''
                SELECT SUM(bytes_sent), SUM(bytes_recv)
                FROM traffic_logs
                WHERE mac = ?
            ''', (mac,))
        row = self.cursor.fetchone()
        return {
            'bytes_sent': row[0] or 0,
            'bytes_recv': row[1] or 0
        }

    # ---------- Métodos para Limits ----------

    def set_limit(self, mac: str, limit_type: str, bytes_max: int):
        """Define um limite para um dispositivo. Se já existir um ativo do mesmo tipo, atualiza."""
        # Desativar limites anteriores do mesmo tipo e MAC
        self.cursor.execute('''
            UPDATE limits SET active = 0
            WHERE mac = ? AND limit_type = ?
        ''', (mac, limit_type))
        # Inserir novo limite
        self.cursor.execute('''
            INSERT INTO limits (mac, limit_type, bytes_max, active)
            VALUES (?, ?, ?, 1)
        ''', (mac, limit_type, bytes_max))
        self.conn.commit()
        logger.info(f"Limite definido: {mac} -> {limit_type} = {bytes_max} bytes")

    def get_limits(self, mac: str = None) -> list[dict]:
        """Retorna os limites ativos. Se mac for fornecido, filtra por esse dispositivo."""
        if mac:
            self.cursor.execute('''
                SELECT * FROM limits WHERE mac = ? AND active = 1
            ''', (mac,))
        else:
            self.cursor.execute('''
                SELECT * FROM limits WHERE active = 1
            ''')
        rows = self.cursor.fetchall()
        columns = ['id', 'mac', 'limit_type', 'bytes_max', 'active']
        return [dict(zip(columns, row)) for row in rows]

    def remove_limit(self, mac: str, limit_type: str = None):
        """Remove (desativa) limites para um MAC. Se limit_type for None, remove todos."""
        if limit_type:
            self.cursor.execute('''
                UPDATE limits SET active = 0 WHERE mac = ? AND limit_type = ?
            ''', (mac, limit_type))
        else:
            self.cursor.execute('''
                UPDATE limits SET active = 0 WHERE mac = ?
            ''', (mac,))
        self.conn.commit()
        logger.info(f"Limite removido: {mac}")

    # ---------- Métodos para Alerts Log ----------

    def log_alert(self, mac: str, alert_type: str, message: str, channel: str = 'telegram', success: bool = True):
        """Regista um alerta enviado (ou tentativa) no histórico."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO alerts_log (timestamp, mac, alert_type, message, channel, success)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp, mac, alert_type, message, channel, int(success)))
        self.conn.commit()
        logger.debug(f"Alerta registado: {mac} -> {alert_type}")

    def get_alerts(self, limit: int = 50) -> list[dict]:
        """Retorna os últimos alertas registados."""
        self.cursor.execute('''
            SELECT * FROM alerts_log ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        rows = self.cursor.fetchall()
        columns = ['id', 'timestamp', 'mac', 'alert_type', 'message', 'channel', 'success']
        return [dict(zip(columns, row)) for row in rows]

    # ---------- Métodos para Pending Alerts (retry) ----------

    def add_pending_alert(self, mac: str, alert_type: str, message: str, channel: str = 'telegram'):
        """Adiciona um alerta à fila de retry."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO pending_alerts (created_at, mac, alert_type, message, channel, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (now, mac, alert_type, message, channel))
        self.conn.commit()
        logger.debug(f"Alerta pendente adicionado: {mac}")

    def get_pending_alerts(self, max_attempts: int = 3) -> list[dict]:
        """Retorna alertas pendentes com menos de max_attempts tentativas."""
        self.cursor.execute('''
            SELECT * FROM pending_alerts
            WHERE status = 'pending' AND attempts < ?
            ORDER BY created_at ASC
        ''', (max_attempts,))
        rows = self.cursor.fetchall()
        columns = ['id', 'created_at', 'mac', 'alert_type', 'message', 'channel', 'attempts', 'last_attempt', 'status']
        return [dict(zip(columns, row)) for row in rows]

    def update_pending_alert(self, alert_id: int, success: bool):
        """Atualiza o status de um alerta pendente após tentativa de envio."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if success:
            self.cursor.execute('''
                UPDATE pending_alerts SET status = 'sent', attempts = attempts + 1, last_attempt = ?
                WHERE id = ?
            ''', (now, alert_id))
        else:
            self.cursor.execute('''
                UPDATE pending_alerts SET attempts = attempts + 1, last_attempt = ?
                WHERE id = ?
            ''', (now, alert_id))
        self.conn.commit()

    # ---------- Limpeza ----------

    def cleanup_old_data(self, retention_days: int = 30):
        """
        Remove tráfego antigo e alertas processados com base na retenção configurada.
        """
        cutoff = datetime.now().timestamp() - (retention_days * 86400)
        cutoff_str = datetime.fromtimestamp(cutoff).strftime("%Y-%m-%d %H:%M:%S")

        self.cursor.execute('DELETE FROM traffic_logs WHERE timestamp < ?', (cutoff_str,))
        self.cursor.execute('DELETE FROM pending_alerts WHERE status = "sent"')
        self.cursor.execute('DELETE FROM alerts_log WHERE timestamp < ?', (cutoff_str,))
        self.conn.commit()
        logger.info(f"Limpeza de dados antigos executada (retenção: {retention_days} dias).")

    def close(self):
        """Fecha a ligação à base de dados."""
        self.conn.close()
        logger.debug("Ligação à base de dados fechada.")


# ----- Função auxiliar para compatibilidade com código antigo (remover após refatoração completa) -----

def save_to_db(mac, nome, ip, bytes_enviados, bytes_recebidos):
    """
    Função de compatibilidade. Usa a nova classe Database para persistir um dispositivo simples.
    Será removida quando todos os módulos usarem Database diretamente.
    """
    db = Database()
    db.save_device(mac, nome, ip)
    db.save_traffic(mac, bytes_enviados, bytes_recebidos)
    db.close()