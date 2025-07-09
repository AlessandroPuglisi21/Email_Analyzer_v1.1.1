import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
from main import avvia_elaborazione_email_cartella

# Dummy function, replace with your real one!
def avvia_elaborazione_email(cartella):
    import time
    time.sleep(2)
    files = [f for f in os.listdir(cartella) if f.endswith('.eml') or f.endswith('.msg')]
    lette = len(files) // 2
    rifiutate = len(files) - lette
    return lette, rifiutate

class ModernEmailAnalyzer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📧 Email Analyzer")
        self.geometry("540x370")
        self.configure(bg="#222831")
        self.resizable(False, False)
        self.cartella = ""
        self.in_esecuzione = False

        # Font
        self.font_title = ("Segoe UI", 20, "bold")
        self.font_label = ("Segoe UI", 13)
        self.font_button = ("Segoe UI", 13, "bold")
        self.font_status = ("Segoe UI", 14, "bold")

        # Titolo
        tk.Label(self, text="Email Analyzer", font=self.font_title, bg="#222831", fg="#00adb5").pack(pady=(18, 2))

        # Selettore cartella
        frame_cartella = tk.Frame(self, bg="#222831")
        frame_cartella.pack(pady=(10, 0), padx=30, fill="x")
        self.btn_cartella = tk.Button(
            frame_cartella, text="📂 Scegli cartella mail", command=self.scegli_cartella,
            bg="#393e46", fg="#eeeeee", font=self.font_button, bd=0, activebackground="#00adb5", activeforeground="#222831",
            cursor="hand2", padx=18, pady=8
        )
        self.btn_cartella.pack(side="left")
        self.lbl_cartella = tk.Label(
            frame_cartella, text="Nessuna cartella selezionata", anchor="w",
            bg="#222831", fg="#eeeeee", font=self.font_label, padx=10
        )
        self.lbl_cartella.pack(side="left", padx=12)

        # Stato
        self.lbl_stato = tk.Label(self, text="Stato: In attesa", bg="#222831", fg="#00adb5", font=self.font_status)
        self.lbl_stato.pack(pady=(22, 8))

        # Risultati
        results_frame = tk.Frame(self, bg="#222831")
        results_frame.pack(pady=2)
        self.lbl_lette = tk.Label(results_frame, text="📬 Mail lette: -", bg="#222831", fg="#eeeeee", font=self.font_label)
        self.lbl_lette.pack(pady=2)
        self.lbl_rifiutate = tk.Label(results_frame, text="🚫 Mail rifiutate: -", bg="#222831", fg="#eeeeee", font=self.font_label)
        self.lbl_rifiutate.pack(pady=2)

        # Bottone avvio
        self.btn_avvia = tk.Button(
            self, text="▶️ Avvia scansione", font=self.font_button,
            bg="#00adb5", fg="#222831", activebackground="#393e46", activeforeground="#eeeeee",
            command=self.avvia_scansione, bd=0, padx=30, pady=12, cursor="hand2"
        )
        self.btn_avvia.pack(pady=28)

        # Footer
        tk.Label(self, text="by Your Company", font=("Segoe UI", 9), bg="#222831", fg="#393e46").pack(side="bottom", pady=6)

    def scegli_cartella(self):
        cartella = filedialog.askdirectory(title="Seleziona la cartella delle email")
        if cartella:
            self.cartella = cartella
            self.lbl_cartella.config(text=cartella)

    def avvia_scansione(self):
        if self.in_esecuzione:
            messagebox.showinfo("Attendi", "Elaborazione già in corso.")
            return
        if not self.cartella or not os.path.isdir(self.cartella):
            messagebox.showwarning("Attenzione", "Seleziona una cartella valida prima di avviare la scansione.")
            return
        self.in_esecuzione = True
        self.lbl_stato.config(text="Stato: In esecuzione...", fg="#ffd369")
        self.lbl_lette.config(text="📬 Mail lette: -")
        self.lbl_rifiutate.config(text="🚫 Mail rifiutate: -")
        self.btn_avvia.config(state="disabled")
        threading.Thread(target=self._elabora, daemon=True).start()

    def _elabora(self):
        try:
            lette, rifiutate = avvia_elaborazione_email_cartella(self.cartella)
            self.lbl_lette.config(text=f"📬 Mail lette: {lette}")
            self.lbl_rifiutate.config(text=f"🚫 Mail rifiutate: {rifiutate}")
            self.lbl_stato.config(text="Stato: Finito", fg="#00adb5")
        except Exception as e:
            self.lbl_stato.config(text="Stato: Errore", fg="#ff2e63")
            messagebox.showerror("Errore", str(e))
        finally:
            self.in_esecuzione = False
            self.btn_avvia.config(state="normal")

if __name__ == "__main__":
    app = ModernEmailAnalyzer()
    app.mainloop()
