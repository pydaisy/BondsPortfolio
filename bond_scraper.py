import requests
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

def measure_time(func):
    """
    Dekorator do mierzenia czasu wykonania funkcji.

    Funkcja wyświetla czas, jaki zajęło wykonanie oznaczonej nią metody lub funkcji.
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Czas wykonania {func.__name__}: {end_time - start_time:.4f} sekundy")
        return result
    return wrapper


class BondScraper:
    """
    Klasa BondScraper odpowiada za scrapowanie danych o obligacjach z podanej strony internetowej.

    Główne funkcjonalności:
    - Pobieranie tabeli z danymi o obligacjach.
    - Zbieranie szczegółowych danych dla konkretnej obligacji.
    """
    def __init__(self, url="https://gpwcatalyst.pl/notowania-obligacji-obligacje-korporacyjne"):
        self.url = url  # Domyślny URL

    @measure_time
    def fetch_bonds(self):
        """
        Pobiera dane ogólne o obligacjach z podanej strony internetowej.

        Metoda wykorzystuje bibliotekę BeautifulSoup do przetwarzania HTML, wyszukuje tabelę
        z danymi o obligacjach i przekształca ją w DataFrame.

        Zwraca:
        - DataFrame zawierający przetworzone dane o obligacjach.
        """
        response = requests.get(self.url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'tab-1000'})

        if not table:
            raise ValueError("Nie znaleziono tabeli o ID 'tab-1000' na stronie.")

        headers = [header.text.strip() for header in table.find_all('th')][1:]  # Pomijamy pierwszy nagłówek
        if not headers:
            raise ValueError("Nie udało się znaleźć nagłówków tabeli.")

        data = []
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            row_data = [cell.text.strip() for cell in cells]

            # Obsługuje przypadki, w których liczba komórek w wierszu jest mniejsza niż oczekiwano
            if len(row_data) == 21:
                pass
            elif len(row_data) == 20:
                row_data.insert(0, data[-1][0] if data else None)
            elif len(row_data) == 19:
                row_data.insert(0, data[-1][1] if data else None)
                row_data.insert(0, data[-1][0] if data else None)

            # Dopasowanie liczby komórek do liczby nagłówków
            if len(row_data) < len(headers):
                row_data.extend([None] * (len(headers) - len(row_data)))
            elif len(row_data) > len(headers):
                row_data = row_data[:len(headers)]

            if row_data:
                data.append(row_data)

        # Przekształcamy dane do DataFrame
        bonds_df = pd.DataFrame(data, columns=headers).drop_duplicates()

        # Przetwarzanie tabeli zgodnie z wymaganiami
        bonds_df = bonds_df.iloc[3:, :]  # Usuń 3 pierwsze wiersze
        bonds_df = bonds_df.iloc[:, :-2]  # Usuń 2 ostatnie kolumny

        # Nadaj nowe nagłówki
        new_headers = [
            'emitent', 'nazwa', 'segment', 'jednostka transakcyjna', 'kurs odniesienia**',
            'kurs otwarcia**', 'kurs min', 'kurs max', 'data/czas ost. trans.', 'wolumen ost. trans.',
            'kurs ostatni*', 'zmiana', 'najlepsza oferta kupna liczba zleceń', 'najlepsza oferta kupna wolumen',
            'najlepsza oferta kupna limit', 'najlepsza oferta sprzedaży limit', 'najlepsza oferta sprzedaży wolumen',
            'najlepsza oferta sprzedaży liczba zleceń', 'limit transakcji', 'obrót skumulowany wolumen',
            'obrót skumulowany wartość (tys. PLN)'
        ]
        bonds_df.columns = new_headers

        # Dzieli nazwę na pierwszą część (emitent)
        bonds_df['nazwa'] = bonds_df['nazwa'].str.split().str[0]

        # Resetowanie indeksu
        bonds_df.reset_index(drop=True, inplace=True)

        return bonds_df

    @measure_time
    def scrape_details(self, bond_name):
        """
        Pobiera szczegółowe dane o wybranej obligacji.

        Argumenty:
        - bond_name: str - nazwa obligacji.

        Metoda otwiera stronę szczegółową obligacji za pomocą przeglądarki Selenium,
        a następnie pobiera dane o oprocentowaniu, marży i innych szczegółach.

        Zwraca:
        - dict: szczegółowe dane o obligacji.
        """
        base_url = "https://gpwcatalyst.pl/o-instrumentach-instrument?nazwa="
        url = base_url + bond_name
        print(f"Przetwarzanie URL: {url}")

        # Ustawienia przeglądarki
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-fullscreen")

        # Uruchomienie nowej przeglądarki
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            driver.get(url)

            # Kliknięcie zakładki "kalkulatorTab"
            kalkulator_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".kalkulatorTab a"))
            )
            kalkulator_tab.click()

            # Poczekaj na załadowanie treści kalkulatora
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "kalkulatorTab"))
            )
            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            table = soup.find("table", {"class": "notoria-profile"})
            if not table:
                print(f"Tabela nie została znaleziona: {bond_name}")
                return None

            bond_details = {}
            bond_details["Bond Name"] = bond_name

            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) == 2:
                    key = cells[0].text.strip()
                    value = cells[1].text.strip()

                    if "Rodzaj oprocentowania" in key:
                        bond_details["Interest Type"] = value[8:].split(' ', 1)[0]
                    elif "Model prognozy odsetek" in key:
                        bond_details["Model of forecast"] = value[0:].split('/', 1)[0]
                    elif "Marża nominalna" in key:
                        print("Nominal Margin", value)
                        bond_details["Nominal Margin"] = value
                        if "Current Period Interest" not in bond_details:
                            bond_details["Current Period Interest"] = value
                    elif "Oprocentowanie w bieżącym okresie" in key:
                        bond_details["Current Period Interest"] = value
                    elif "Data wykupu" in key:
                        bond_details["Maturity Date"] = value
                    elif "Wartość nominalna" in key:
                        bond_details["Nominal Value"] = value
                    elif "Narosłe odsetki" in key:
                        bond_details["Accrued interest"] = value
                    elif "Liczba wypłat w ciągu roku" in key:
                        bond_details["Payments per year"] = value

            return bond_details

        except Exception as e:
            print(f"Error podczas przetwarzania {bond_name}: {e}")
            return None

        finally:

            driver.quit()
