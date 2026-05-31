"""Kiwoom OpenAPI+ realtime collector for the isolated 32-bit runtime.

This worker intentionally writes JSONL spool files instead of importing the
64-bit server package or writing to the server SQLite database directly.
"""

from __future__ import print_function

import argparse
import json
import os
import sys
import uuid
from datetime import datetime


TRADE_FID_LIST = "10;12;13;15;16;17;18;20;228"


def parse_int(value):
    try:
        cleaned = value.strip().replace("+", "").replace("-", "")
        return abs(int(cleaned)) if cleaned else None
    except Exception:
        return None


def parse_float(value):
    try:
        cleaned = value.strip().replace("+", "").replace("%", "")
        return float(cleaned) if cleaned else None
    except Exception:
        return None


def is_real_type(real_type, expected):
    if real_type == expected:
        return True
    try:
        if real_type.encode("latin1").decode("cp949") == expected:
            return True
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    try:
        if expected.encode("cp949").decode("latin1") == real_type:
            return True
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return False


class JsonlSpoolWriter(object):
    def __init__(self, spool_path):
        self.spool_path = os.path.abspath(spool_path)
        parent = os.path.dirname(self.spool_path)
        if not os.path.isdir(parent):
            os.makedirs(parent)
        self.handle = open(self.spool_path, "a", encoding="utf-8")

    def write_tick(self, tick):
        event = {
            "schema": "kiwoom_tick_v1",
            "source_event_id": uuid.uuid4().hex,
            "market": "KRX",
            "tick": tick,
        }
        self.handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.handle.flush()

    def close(self):
        self.handle.close()


class KiwoomLegacyWorker(object):
    def __init__(
        self,
        app,
        spool_writer,
        codes,
        login_timeout_sec,
        duration_seconds,
        require_existing_login=False,
        require_ticks=False,
    ):
        from PyQt5.QAxContainer import QAxWidget
        from PyQt5.QtCore import QTimer

        self.app = app
        self.QTimer = QTimer
        self.spool_writer = spool_writer
        self.codes = list(codes)
        self.login_timeout_sec = login_timeout_sec
        self.duration_seconds = duration_seconds
        self.require_existing_login = require_existing_login
        self.require_ticks = require_ticks
        self.saved_tick_count = 0
        self.real_event_count = 0
        self.exit_code = 1
        self.login_timer = None
        self.finish_timer = None

        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        if self.ocx.isNull():
            print("KIWOOM_WORKER_OCX_STATUS=failed")
            self.exit_code = 6
            QTimer.singleShot(0, self.app.quit)
            return

        print("KIWOOM_WORKER_OCX_STATUS=created")
        self.ocx.OnEventConnect.connect(self.on_login)
        self.ocx.OnReceiveRealData.connect(self.on_receive_real_data)
        connect_state = self.ocx.dynamicCall("GetConnectState()")
        print("KIWOOM_WORKER_CONNECT_STATE_BEFORE={}".format(connect_state))

        if self._connected(connect_state):
            print("KIWOOM_WORKER_LOGIN_SKIPPED_ALREADY_CONNECTED=True")
            QTimer.singleShot(0, lambda: self.on_login(0))
        elif self.require_existing_login:
            print("KIWOOM_WORKER_ABORTED=existing_login_not_confirmed")
            self.exit_code = 4
            QTimer.singleShot(0, self.app.quit)
        else:
            QTimer.singleShot(0, self.request_login)

    def request_login(self):
        self.login_timer = self.QTimer()
        self.login_timer.setSingleShot(True)
        self.login_timer.timeout.connect(self.on_login_timeout)
        self.login_timer.start(self.login_timeout_sec * 1000)
        print("KIWOOM_WORKER_LOGIN_REQUESTED=True")
        print("KIWOOM_WORKER_LOGIN_REQUEST_RETURN={}".format(self.ocx.dynamicCall("CommConnect()")))

    def on_login(self, err_code):
        if self.login_timer:
            self.login_timer.stop()
        print("KIWOOM_WORKER_LOGIN_RESULT={}".format(err_code))
        if int(err_code) != 0:
            self.exit_code = 2
            self.app.quit()
            return

        code_text = ";".join(self.codes)
        result = self.ocx.dynamicCall(
            "SetRealReg(QString, QString, QString, QString)",
            "9200",
            code_text,
            TRADE_FID_LIST,
            "0",
        )
        print("KIWOOM_WORKER_REALTIME_REGISTER_RESULT={}".format(result))
        print("KIWOOM_WORKER_REALTIME_REGISTER_CODES={}".format(code_text))
        self.finish_timer = self.QTimer()
        self.finish_timer.setSingleShot(True)
        self.finish_timer.timeout.connect(self.finish)
        self.finish_timer.start(self.duration_seconds * 1000)

    def on_receive_real_data(self, code, real_type, real_data):
        self.real_event_count += 1
        if not is_real_type(real_type, "주식체결"):
            return
        tick = {
            "code": code,
            "trade_time": self.get_real_data(code, 20),
            "price": parse_int(self.get_real_data(code, 10)),
            "change_rate": parse_float(self.get_real_data(code, 12)),
            "acc_volume": parse_int(self.get_real_data(code, 13)),
            "tick_volume": parse_int(self.get_real_data(code, 15)),
            "open_price": parse_int(self.get_real_data(code, 16)),
            "high_price": parse_int(self.get_real_data(code, 17)),
            "low_price": parse_int(self.get_real_data(code, 18)),
            "strength": parse_float(self.get_real_data(code, 228)),
            "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        }
        self.spool_writer.write_tick(tick)
        self.saved_tick_count += 1
        if self.saved_tick_count <= 5 or self.saved_tick_count % 100 == 0:
            print("KIWOOM_WORKER_TICK_SAMPLE={},code:{},price:{}".format(
                self.saved_tick_count,
                tick["code"],
                tick["price"],
            ))

    def get_real_data(self, code, fid):
        return self.ocx.dynamicCall("GetCommRealData(QString, int)", code, fid).strip()

    def on_login_timeout(self):
        print("KIWOOM_WORKER_LOGIN_TIMEOUT=True")
        self.exit_code = 3
        self.app.quit()

    def finish(self):
        try:
            self.ocx.dynamicCall("SetRealRemove(QString, QString)", "9200", "ALL")
        except Exception as exc:
            print("KIWOOM_WORKER_REALTIME_CLEAR_ERROR={}".format(exc))
        print("KIWOOM_WORKER_REALTIME_EVENT_COUNT={}".format(self.real_event_count))
        print("KIWOOM_WORKER_SAVED_TICK_COUNT={}".format(self.saved_tick_count))
        self.exit_code = 0 if not self.require_ticks or self.saved_tick_count > 0 else 5
        self.app.quit()

    @staticmethod
    def _connected(value):
        try:
            return int(value) == 1
        except (TypeError, ValueError):
            return False


def parse_args():
    parser = argparse.ArgumentParser(description="Collect Kiwoom realtime ticks into a JSONL spool.")
    parser.add_argument("--codes", default="005930,000660,035420")
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--login-timeout-sec", type=int, default=45)
    parser.add_argument("--require-existing-login", action="store_true")
    parser.add_argument("--require-ticks", action="store_true")
    parser.add_argument(
        "--spool-path",
        default=os.path.join("data", "kiwoom_spool", "kiwoom_ticks.jsonl"),
    )
    return parser.parse_args()


def main():
    from PyQt5.QtWidgets import QApplication

    args = parse_args()
    codes = [item.strip() for item in args.codes.split(",") if item.strip()]
    print("KIWOOM_WORKER_SPOOL_PATH={}".format(os.path.abspath(args.spool_path)))
    print("KIWOOM_WORKER_DURATION_SECONDS={}".format(args.seconds))
    app = QApplication(sys.argv)
    writer = JsonlSpoolWriter(args.spool_path)
    worker = KiwoomLegacyWorker(
        app=app,
        spool_writer=writer,
        codes=codes,
        login_timeout_sec=args.login_timeout_sec,
        duration_seconds=args.seconds,
        require_existing_login=args.require_existing_login,
        require_ticks=args.require_ticks,
    )
    app.exec_()
    writer.close()
    return worker.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
