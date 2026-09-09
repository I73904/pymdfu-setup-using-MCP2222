import os
import subprocess
from datetime import datetime


def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def prompt(label, default):
    value = input(f"{label} [{default}]:\n").strip()
    if not value:
        return default
    if value.lower().startswith("found "):
        value = value[6:].strip()
    return value


def prompt_required(label):
    while True:
        value = input(f"{label}:\n").strip()
        if value:
            return value
        print("Value required. Please enter a path.")


def prompt_list(label, default_list):
    default_text = ",".join(str(v) for v in default_list)
    value = input(f"{label} [{default_text}]:\n").strip()
    if not value:
        return default_list
    parts = [p.strip().replace("_", "") for p in value.split(",") if p.strip()]
    return [int(p) for p in parts]


def prompt_protocols(label, default_list):
    default_text = ",".join(default_list)
    value = input(f"{label} [{default_text}]:\n").strip()
    if not value:
        return default_list
    allowed = {"UART", "SPI", "I2C"}
    return [p.strip().upper() for p in value.split(",") if p.strip().upper() in allowed]


def ensure_file(path, label):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{label} not found: {path}")


def pymdfu_hint():
    user = os.environ.get("USERPROFILE", "C:\\Users\\<your_user>")
    candidates = [
        os.path.join(user, r"AppData\Roaming\Python\Python311\Scripts\pymdfu.exe"),
        os.path.join(user, r"AppData\Roaming\Python\Python312\Scripts\pymdfu.exe"),
        os.path.join(user, r"AppData\Roaming\Python\Python310\Scripts\pymdfu.exe"),
        os.path.join(user, r"AppData\Local\Programs\Python\Python313\Scripts\pymdfu.exe"),
        os.path.join(user, r"AppData\Local\Programs\Python\Python312\Scripts\pymdfu.exe"),
        os.path.join(user, r"AppData\Local\Programs\Python\Python311\Scripts\pymdfu.exe"),
    ]
    existing = [p for p in candidates if os.path.isfile(p)]
    if existing:
        return f"Hint: found {existing[0]}"
    return f"Hint: check {candidates[0]} or {candidates[-1]}"


def detect_pymdfu_path():
    user = os.environ.get("USERPROFILE", "C:\\Users\\<your_user>")
    candidates = [
        os.path.join(user, r"AppData\Roaming\Python\Python313\Scripts\pymdfu.exe"),
        os.path.join(user, r"AppData\Roaming\Python\Python312\Scripts\pymdfu.exe"),
        os.path.join(user, r"AppData\Roaming\Python\Python311\Scripts\pymdfu.exe"),
        os.path.join(user, r"AppData\Roaming\Python\Python310\Scripts\pymdfu.exe"),
        os.path.join(user, r"AppData\Local\Programs\Python\Python313\Scripts\pymdfu.exe"),
        os.path.join(user, r"AppData\Local\Programs\Python\Python312\Scripts\pymdfu.exe"),
        os.path.join(user, r"AppData\Local\Programs\Python\Python311\Scripts\pymdfu.exe"),
        os.path.join(user, r"AppData\Local\Programs\Python\Python310\Scripts\pymdfu.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return ""


def html_escape(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def run_pymdfu(label, cmd, meta, log_path):
    print(f"\n==== {label} ====")
    print(" ".join(cmd))
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{now_ts()}] COMMAND: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = (result.stdout or "") + (result.stderr or "")
    if output.strip():
        print(output.strip())
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now_ts()}] {output.strip()}\n")
    failed = (result.returncode != 0) or ("ERROR -" in output) or ("Upgrade failed" in output)
    if failed:
        print(f"{label} failed (exit={result.returncode})")
        meta["Status"] = "failed"
    else:
        print(f"{label} succeeded.")
        meta["Status"] = "success"
    meta["ExitCode"] = result.returncode
    meta["Output"] = output.strip()


def write_html_report(results, html_path):
    summary_rows = []
    for r in results:
        color = "#1a7f37" if r["Status"] == "success" else "#d1242f"
        summary_rows.append(
            f"<tr><td>{r['Protocol']}</td><td>{r['Speed']}</td><td style='color:{color}'>{r['Status']}</td></tr>"
        )

    detail_rows = []
    for r in results:
        color = "#1a7f37" if r["Status"] == "success" else "#d1242f"
        detail = html_escape(r["Output"])
        detail_rows.append(
            f"<tr><td>{r['Protocol']}</td><td>{r['Speed']}</td><td style='color:{color}'>{r['Status']}</td>"
            f"<td>{r['Timestamp']}</td><td><pre>{detail}</pre></td></tr>"
        )

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>MDFU Update Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 16px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #f5f5f5; text-align: left; }}
    pre {{ white-space: pre-wrap; margin: 0; }}
  </style>
</head>
<body>
  <h2>MDFU Update Report</h2>
  <p>Generated: {now_ts()}</p>
  <h3>Summary</h3>
  <table>
    <thead>
      <tr><th>Protocol</th><th>Speed</th><th>Pass/Fail</th></tr>
    </thead>
    <tbody>
      {"".join(summary_rows)}
    </tbody>
  </table>
  <h3>Details</h3>
  <table>
    <thead>
      <tr><th>Protocol</th><th>Speed</th><th>Status</th><th>Timestamp</th><th>Output</th></tr>
    </thead>
    <tbody>
      {"".join(detail_rows)}
    </tbody>
  </table>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(script_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    stamp = now_stamp()
    log_path = os.path.join(reports_dir, f"mdfu_run_{stamp}.log")
    html_path = os.path.join(reports_dir, f"mdfu_run_{stamp}.html")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{now_ts()}] MDFU update run started\n")

    detected = detect_pymdfu_path()
    if detected:
        print(f"Hint: found {detected}")
    else:
        print("Hint: pymdfu.exe not auto-detected. Install with: py -m pip install pymdfu")
    pymdfu_exe = prompt("Path to pymdfu.exe", detected)
    print("Find UART COM port: Device Manager > Ports (COM & LPT) > Curiosity Nano CDC/USB Serial Device.")
    print("Or: MPLAB Data Visualizer > Port list.")
    com_port = prompt("UART COM port (CDC)", "COM29")

    print("Press Enter to run all protocols (UART,SPI,I2C).")
    protocols = prompt_protocols("Protocols to run (UART,SPI,I2C)", ["UART", "SPI", "I2C"])
    uart_bauds = []
    spi_speeds = []
    i2c_speeds = []

    uart_image = ""
    spi_image = ""
    i2c_image = ""

    if "UART" in protocols:
        uart_bauds = prompt_list("UART baud rates (comma-separated)", [2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600])
        uart_image = prompt_required("UART application image path")
    if "SPI" in protocols:
        spi_speeds = prompt_list("SPI speeds (comma-separated, Hz)", [187500, 375000, 750000, 1500000, 3000000, 6000000, 12000000])
        spi_image = prompt_required("SPI application image path")
    if "I2C" in protocols:
        i2c_speeds = prompt_list("I2C speeds (comma-separated, Hz)", [100000, 400000, 1000000])
        i2c_image = prompt_required("I2C application image path")

    print("\nKeep the bootloader HEX file for the selected protocol ready to program.")
    uart_boot = ""
    spi_boot = ""
    i2c_boot = ""

    ensure_file(pymdfu_exe, "pymdfu.exe")
    if "UART" in protocols:
        ensure_file(uart_image, "UART image")
    if "SPI" in protocols:
        ensure_file(spi_image, "SPI image")
    if "I2C" in protocols:
        ensure_file(i2c_image, "I2C image")

    print("Starting MDFU updates...")
    print(f"UART image: {uart_image}")
    print(f"SPI image:  {spi_image}")
    print(f"I2C image:  {i2c_image}")

    results = []

    if "UART" in protocols:
        for baud in uart_bauds:
            print(f"\nProgram the UART MDFU bootloader (baud {baud}), then press Enter to continue:")
            input()
            meta = {"Protocol": "UART", "Speed": baud, "Timestamp": now_ts()}
            cmd = [
                pymdfu_exe, "-v", "debug", "update",
                "--tool", "serial", "--port", com_port,
                "--baudrate", str(baud), "--image", uart_image
            ]
            run_pymdfu(f"UART Update @ {baud}", cmd, meta, log_path)
            results.append(meta)

    if "SPI" in protocols:
        for speed in spi_speeds:
            print(f"\nProgram the SPI MDFU bootloader (speed {speed}), then press Enter to continue:")
            input()
            meta = {"Protocol": "SPI", "Speed": speed, "Timestamp": now_ts()}
            cmd = [
                pymdfu_exe, "-v", "debug", "update",
                "--tool", "mcp2222", "--interface", "spi",
                "--image", spi_image, "--clk-speed", str(speed),
                "--mode", "0", "--cs-pin", "0", "--cs-polarity", "low", "--delay", "0"
            ]
            run_pymdfu(f"SPI Update @ {speed}", cmd, meta, log_path)
            results.append(meta)

    if "I2C" in protocols:
        for speed in i2c_speeds:
            print(f"\nProgram the I2C MDFU bootloader (speed {speed}), then press Enter to continue:")
            input()
            meta = {"Protocol": "I2C", "Speed": speed, "Timestamp": now_ts()}
            cmd = [
                pymdfu_exe, "-v", "debug", "update",
                "--tool", "mcp2222", "--interface", "i2c",
                "--clk-speed", str(speed), "--address", "32",
                "--image", i2c_image
            ]
            run_pymdfu(f"I2C Update @ {speed}", cmd, meta, log_path)
            results.append(meta)

    write_html_report(results, html_path)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{now_ts()}] MDFU update run completed\n")
    print(f"\nReport written to: {html_path}")
    print(f"Log written to:    {log_path}")
    print("\nAll requested updates attempted.")


if __name__ == "__main__":
    main()
