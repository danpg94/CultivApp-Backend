import flet as ft
import json
import httpx  # En lugar de requests, para que funcione en Android

def main(page: ft.Page):

    page.title = "Cherry"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "auto"
    page.window_height = 600
    page.window_width = 400

    # Crear el FilePicker
    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    # Función para volver a la pantalla principal
    def volver_inicio(e=None):
        page.controls.clear()

        titulo = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Text("\n\n🍒", size=32),
                ft.Text("\n\nCherry", size=32, weight="bold")
            ]
        )

        espacio = ft.Container(height=40)  # Espacio debajo del título

        botones = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                ft.ElevatedButton("📂 Abrir archivo JSON local", on_click=abrir_archivo),
                ft.ElevatedButton("📡 Cargar datos desde red", on_click=cargar_desde_red)
            ]
        )

        page.controls.extend([titulo, espacio, botones])
        page.update()

    # Mostrar los datos en la interfaz
    def mostrar_datos(datos):
        lista = ft.ListView(expand=True, spacing=10)
        for i, registro in enumerate(datos["datos"]):
            lista.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(f"Registro {i+1}", weight="bold"),
                            ft.Text(f"🌡️ Temperatura: {registro['temperatura']}%"),
                            ft.Text(f"💧 Humedad: {registro['humedad']}%"),
                            ft.Text(f"🔆 Luminosidad: {registro['luminosidad']}%"),
                        ]),
                        padding=10
                    )
                )
            )

        page.controls.clear()
        page.add(
            ft.ElevatedButton("← Volver", on_click=volver_inicio),
            lista
        )
        page.update()

    # Manejar archivo local
    def archivo_seleccionado(e: ft.FilePickerResultEvent):
        if e.files:
            ruta = e.files[0].path
            try:
                with open(ruta, "r") as f:
                    datos = json.load(f)
                    mostrar_datos(datos)
            except Exception as err:
                mostrar_error(f"Error leyendo archivo: {err}")
        else:
            mostrar_error("No se seleccionó ningún archivo.")

    file_picker.on_result = archivo_seleccionado

    def abrir_archivo(e):
        file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["json"]
        )

    # Manejar carga desde red con httpx
    def cargar_desde_red(e):
        try:
            url = "http://192.168.1.100:5000/datos"  # <-- cámbiala cuando tu compañero esté listo
            with httpx.Client() as client:
                r = client.get(url, timeout=5)
                datos = r.json()
                mostrar_datos(datos)
        except Exception as err:
            mostrar_error(f"No se pudo conectar al servidor:\n{err}")

    # Mostrar mensaje de error
    def mostrar_error(msg):
        page.dialog = ft.AlertDialog(
            title=ft.Text("❌ Error"),
            content=ft.Text(msg),
            on_dismiss=lambda e: None
        )
        page.dialog.open = True
        page.update()

    # Mostrar la pantalla principal al iniciar
    volver_inicio()

ft.app(target=main)
