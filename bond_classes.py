import pandas as pd
from datetime import date, datetime
import streamlit as st
from scipy.optimize import root_scalar
from dateutil.relativedelta import relativedelta


def log_execution(func):
    """Dekorator do logowania wywołań funkcji."""

    def wrapper(*args, **kwargs):
        print(f"Wywołanie funkcji: {func.__name__}")
        print(f"Argumenty pozycyjne: {args}")
        result = func(*args, **kwargs)
        print(f"Zwrócony wynik: {result}")
        return result

    return wrapper


# Klasa bazowa Bond
class Bond:
    def __init__(self, emitent, nazwa, segment, kurs_otwarcia, kurs_odniesienia, kurs_ostatni, data_ostatniej_transakcji, kurs_min, kurs_max,
                 najlepsza_oferta_kupna_limit,
                 najlepsza_oferta_kupna_wolumen, najlepsza_oferta_sprzedazy_limit, najlepsza_oferta_sprzedazy_wolumen,
                 zmiana, wolumen, obrot,
                 nominal_value = None, maturity_date = None, interest_type = None, nominal_margin = None,
                 current_interest = None, payments_per_year = None, accrued_interest = None, typ_dzialalnosci = None,
                 model_of_forecast = None, reference_rate_model = None):
        self.emitent = emitent
        self.nazwa = nazwa
        self.segment = segment
        self.kurs_otwarcia = kurs_otwarcia
        self.kurs_odniesienia = float(kurs_odniesienia.replace(',', '.')) if isinstance(kurs_odniesienia, str) else kurs_odniesienia
        self.kurs_ostatni = float(kurs_ostatni.replace(',', '.') if isinstance(kurs_ostatni, str) else kurs_ostatni) if kurs_ostatni != "-" else "-"
        self.data_ostatniej_transakcji = data_ostatniej_transakcji
        self.kurs_min = float(kurs_min.replace(',', '.') if isinstance(kurs_min, str) else kurs_min) if kurs_min != "-" else "-"
        self.kurs_max = float(kurs_max.replace(',', '.') if isinstance(kurs_max, str) else kurs_max) if kurs_max != "-" else "-"
        self.najlepsza_oferta_kupna_limit = najlepsza_oferta_kupna_limit
        self.najlepsza_oferta_kupna_wolumen = najlepsza_oferta_kupna_wolumen
        self.najlepsza_oferta_sprzedazy_limit = najlepsza_oferta_sprzedazy_limit
        self.najlepsza_oferta_sprzedazy_wolumen = najlepsza_oferta_sprzedazy_wolumen
        self.zmiana = zmiana
        self.wolumen = wolumen
        self.obrot = obrot
        self.nominal_value = float(nominal_value.replace(',', '')) if nominal_value else None
        self.maturity_date = (
            datetime.strptime(maturity_date, "%Y-%m-%d").date()
            if isinstance(maturity_date, str) else maturity_date
        )
        self.interest_type = interest_type
        self.nominal_margin = float(nominal_margin.replace('%', '')) if nominal_margin else None
        self.current_interest = float(current_interest.replace('%', '')) if current_interest else None
        self.payments_per_year = float(payments_per_year) if payments_per_year else None
        self.accrued_interest = (
            float(accrued_interest.replace(',', '')) if accrued_interest else None
        )
        self.typ_dzialalnosci = typ_dzialalnosci
        self.model_of_forecast = model_of_forecast
        self.reference_rate_model = reference_rate_model

    @log_execution
    def years_to_maturity(self, current_date):
        """Oblicza liczbę lat do zapadalności."""
        from datetime import datetime
        if isinstance(self.maturity_date, str):
            maturity_date = datetime.strptime(self.maturity_date, '%Y-%m-%d').date()
        else:
            maturity_date = self.maturity_date
        return (maturity_date - current_date).days / 365.0

    @log_execution
    def generate_coupon_dates(self):
        """Generuje listę dat płatności kuponów."""
        if not self.maturity_date or not self.payments_per_year:
            raise ValueError("Nie zdefiniowano daty zapadalności lub liczby płatności.")

        maturity_date = self.maturity_date
        payments_per_year = self.payments_per_year

        coupon_dates = []
        # Ustalamy datę początkową na datę zapadalności minus okres płatności
        current_date = maturity_date - relativedelta(
            months = 12 // payments_per_year)  # Pierwsza płatność przed zapadalnością

        total_payments = int(self.years_to_maturity(datetime.today().date()) * payments_per_year)

        for _ in range(total_payments):
            coupon_dates.append(current_date)
            current_date += relativedelta(months = int(12 / payments_per_year))

        return sorted(coupon_dates)


# Klasa dla obligacji stałoprocentowych
class FixedRateBond(Bond):
    @log_execution
    def calculate_coupon(self):
        """Oblicza wartość kuponu dla obligacji stałoprocentowych."""
        if self.nominal_value and self.current_interest and self.payments_per_year:
            return (self.nominal_value * self.current_interest / 100) / self.payments_per_year
        return None

    @log_execution
    def ytm_brutto(self, purchase_price, max_iterations = 100, tolerance = 1e-6):
        """Oblicza YTM dla obligacji stałoprocentowej."""
        from scipy.optimize import newton

        purchase_price = purchase_price * self.nominal_value / 100

        coupon = self.calculate_coupon()  # Kupon dla jednego okresu
        if coupon is None:
            raise ValueError("Kupon nie został poprawnie obliczony.")

        years_to_maturity = self.years_to_maturity(datetime.today().date())
        if not years_to_maturity:
            raise ValueError("Nie można obliczyć liczby lat do zapadalności.")

        payments_per_year = self.payments_per_year
        if not payments_per_year:
            raise ValueError("Nie zdefiniowano liczby płatności w ciągu roku.")

        total_periods = int(round(years_to_maturity * payments_per_year) + 1)  # Zaokrąglenie liczby okresów

        def price_difference(ytm):
            # Przeliczenie YTM na okresowe (ytm_per_period)
            ytm_per_period = ytm / payments_per_year
            # Obliczenie wartości bieżącej płatności kuponowych
            price = sum(
                coupon / ((1 + ytm_per_period) ** t) for t in range(1, total_periods + 1)
            )
            # Dodanie wartości nominalnej dyskontowanej do wartości bieżącej
            price += self.nominal_value / ((1 + ytm_per_period) ** total_periods)
            return price - purchase_price

        # Ustawienie punktu startowego
        try:
            annual_ytm = newton(price_difference, x0 = 0.045, maxiter = max_iterations, tol = tolerance)
        except RuntimeError:
            raise ValueError("Metoda Newtona nie znalazła rozwiązania.")

        return round(annual_ytm * 100, 2)  # Zwrot jako procent z dwoma miejscami po przecinku

    @log_execution
    def ytm_netto(self, purchase_price, tax_rate = 0.19, max_iterations = 100, tolerance = 1e-6):
        """
        Oblicza YTM netto (po uwzględnieniu podatku) dla obligacji stałoprocentowej.

        :param purchase_price: Cena zakupu obligacji.
        :param tax_rate: Stawka podatkowa (domyślnie 19%).
        :return: YTM netto w procentach.
        """
        from scipy.optimize import newton

        coupon = self.calculate_coupon()  # Kupon dla jednego okresu
        coupon = coupon * (1 - tax_rate)  # Zastosowanie podatku do kuponu
        if coupon is None:
            raise ValueError("Kupon nie został poprawnie obliczony.")

        years_to_maturity = self.years_to_maturity(datetime.today().date())
        if not years_to_maturity:
            raise ValueError("Nie można obliczyć liczby lat do zapadalności.")

        payments_per_year = self.payments_per_year
        if not payments_per_year:
            raise ValueError("Nie zdefiniowano liczby płatności w ciągu roku.")

        total_periods = int(round(years_to_maturity * payments_per_year))  # Zaokrąglenie liczby okresów

        def price_difference(ytm):
            # Przeliczenie YTM na okresowe (ytm_per_period)
            ytm_per_period = ytm / payments_per_year
            # Obliczenie wartości bieżącej płatności kuponowych
            price = sum(
                coupon / ((1 + ytm_per_period) ** t) for t in range(1, total_periods + 1)
            )
            # Dodanie wartości nominalnej dyskontowanej do wartości bieżącej
            price += self.nominal_value / ((1 + ytm_per_period) ** total_periods)
            return price - purchase_price

        # Ustawienie punktu startowego
        try:
            annual_ytm = newton(price_difference, x0 = 0.045, maxiter = max_iterations, tol = tolerance)
        except RuntimeError:
            raise ValueError("Metoda Newtona nie znalazła rozwiązania.")

        return round(annual_ytm * 100, 2)

    @log_execution
    def ekwivalent_ytm_brutto(self, purchase_price, tax_rate = 0.19):
        """
        Oblicza ekwiwalent rentowności do wykupu brutto (GEY) na podstawie ceny zakupu obligacji.

        :param purchase_price: Cena zakupu obligacji.
        :param tax_rate: Stawka podatkowa (domyślnie 19%).
        :return: Ekwiwalent YTM brutto w procentach.
        """
        if tax_rate >= 1 or tax_rate < 0:
            raise ValueError("Stawka podatkowa musi być w zakresie od 0 do 1.")

        # Oblicz YTM netto
        ytm_netto = self.ytm_netto(purchase_price, tax_rate)

        # Oblicz ekwiwalent YTM brutto
        return ytm_netto / (1 - tax_rate)

    @log_execution
    def macaulay_duration(self, purchase_price):
        """
        Oblicza czas trwania Macaulay'a dla obligacji stałoprocentowej.

        :param purchase_price: Cena zakupu obligacji (czysta cena).
        :return: Czas trwania Macaulay'a (w latach).
        """
        # Oblicz kupon
        coupon = self.calculate_coupon()
        if not coupon:
            raise ValueError("Nie można obliczyć kuponu.")

        # Oblicz YTM w skali dziesiętnej
        ytm = self.ytm_brutto(purchase_price) / 100

        # Generuj daty płatności kuponów
        coupon_dates = self.generate_coupon_dates()

        # Obliczanie przepływów pieniężnych i czasu w latach
        cash_flows = []
        times = []
        for i, date in enumerate(coupon_dates, start = 1):
            time_in_years = i / self.payments_per_year
            if i == len(coupon_dates):  # Ostatnia płatność zawiera wartość nominalną
                cash_flows.append(coupon + self.nominal_value)
            else:
                cash_flows.append(coupon)
            times.append(time_in_years)

        # Oblicz Macaulay duration
        numerator = sum(cf * t / (1 + ytm / self.payments_per_year) ** (t * self.payments_per_year)
                        for cf, t in zip(cash_flows, times))
        denominator = sum(cf / (1 + ytm / self.payments_per_year) ** (t * self.payments_per_year)
                          for cf, t in zip(cash_flows, times))

        macaulay_duration_years = numerator / denominator
        return macaulay_duration_years

    @log_execution
    def modified_duration(self, purchase_price, ytm = None):
        """
        Oblicza zmodyfikowany czas trwania obligacji.

        :param purchase_price: Cena zakupu obligacji (czysta cena).
        :param ytm: Rentowność do wykupu w skali rocznej (jeśli znana, w przeciwnym razie obliczana automatycznie).
        :return: Zmodyfikowany czas trwania obligacji.
        """
        if ytm is None:
            ytm = self.ytm_brutto(purchase_price) / 100  # Konwersja z procentów na liczbę dziesiętną

        payments_per_year = self.payments_per_year
        if not payments_per_year:
            raise ValueError("Nie zdefiniowano liczby płatności w ciągu roku.")

        # Obliczenie czasu trwania Macaulay'a
        macaulay_duration_years = self.macaulay_duration(purchase_price)

        # Obliczenie zmodyfikowanego czasu trwania
        modified_duration_years = macaulay_duration_years / (1 + ytm / payments_per_year)

        return modified_duration_years

    # Klasa dla obligacji zmiennoprocentowych


class FloatingRateBond(Bond):
    def __init__(self, *args, model_of_forecast = None, reference_rate_model = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_of_forecast = model_of_forecast
        self.reference_rate_model = reference_rate_model

    @log_execution
    def calculate_coupon(self):
        if self.nominal_value and self.reference_rate_model is not None:
            return self.nominal_value * (self.reference_rate_model + self.nominal_margin) / 100
        return None

    @log_execution
    def ytm_brutto(self, purchase_price):
        """Oblicza YTM brutto dla obligacji zmiennoprocentowych."""
        years_to_maturity = self.years_to_maturity(date.today())
        if not years_to_maturity or not self.reference_rate_model:
            raise ValueError("Nie można obliczyć YTM dla obligacji zmiennoprocentowej.")

        payments_per_year = self.payments_per_year or 1  # Domyślnie 1 płatność rocznie
        periods = int(years_to_maturity * payments_per_year)
        purchase_price = purchase_price * self.nominal_value / 100

        def price_difference(ytm):
            price = 0
            for period in range(1, periods + 1):
                # Oblicz kupon dla danego okresu
                reference_rate = self.reference_rate_model  # .get_rate(period)
                coupon = self.nominal_value * (reference_rate + self.nominal_margin) / 100 / payments_per_year
                # Dyskontuj kupon
                price += coupon / ((1 + ytm / payments_per_year) ** period)
            # Dyskontuj wartość nominalną
            price += self.nominal_value / ((1 + ytm / payments_per_year) ** periods)
            return price - purchase_price

        # Znajdź YTM przy użyciu metody Brent'a
        result = root_scalar(price_difference, bracket = [0.000001, 1], method = 'brentq')
        if not result.converged:
            raise RuntimeError("Obliczenie YTM nie powiodło się.")

        return result.root * 100

    @log_execution
    def ytm_netto(self, purchase_price, tax_rate = 0.19):
        """Oblicza YTM brutto dla obligacji zmiennoprocentowych."""
        years_to_maturity = self.years_to_maturity(date.today())
        if not years_to_maturity or not self.reference_rate_model:
            raise ValueError("Nie można obliczyć YTM dla obligacji zmiennoprocentowej.")

        payments_per_year = self.payments_per_year or 1  # Domyślnie 1 płatność rocznie
        periods = int(years_to_maturity * payments_per_year)
        purchase_price = purchase_price * self.nominal_value / 100

        def price_difference(ytm):
            price = 0
            for period in range(1, periods + 1):
                # Oblicz kupon dla danego okresu
                reference_rate = self.reference_rate_model  # .get_rate(period)
                coupon = self.nominal_value * (reference_rate + self.nominal_margin) / 100 / payments_per_year
                coupon = coupon * (1 - tax_rate)
                # Dyskontuj kupon
                price += coupon / ((1 + ytm / payments_per_year) ** period)
            # Dyskontuj wartość nominalną
            price += self.nominal_value / ((1 + ytm / payments_per_year) ** periods)
            return price - purchase_price

        # Znajdź YTM przy użyciu metody Brent'a
        result = root_scalar(price_difference, bracket = [0.0001, 1], method = 'brentq')
        if not result.converged:
            raise RuntimeError("Obliczenie YTM nie powiodło się.")

        return result.root * 100

    @log_execution
    def ekwivalent_ytm_brutto(self, purchase_price, tax_rate = 0.19):
        """
        Oblicza ekwiwalent rentowności do wykupu brutto (GEY) na podstawie ceny zakupu obligacji.

        :param purchase_price: Cena zakupu obligacji.
        :param tax_rate: Stawka podatkowa (domyślnie 19%).
        :return: Ekwiwalent YTM brutto w procentach.
        """
        if tax_rate >= 1 or tax_rate < 0:
            raise ValueError("Stawka podatkowa musi być w zakresie od 0 do 1.")

        # Oblicz YTM netto
        ytm_netto = self.ytm_netto(purchase_price, tax_rate)

        # Oblicz ekwiwalent YTM brutto
        return ytm_netto / (1 - tax_rate)

    @log_execution
    def macaulay_duration(self, purchase_price):
        """Oblicza YTM brutto dla obligacji zmiennoprocentowych."""
        return self.ytm_brutto(purchase_price) / (1 - 0.19) * 0.19

    @log_execution
    def modified_duration(self, purchase_price):
        """Oblicza YTM brutto dla obligacji zmiennoprocentowych."""
        return self.ytm_brutto(purchase_price) / (1 - 0.19) * 0.19


# Klasa BondPortfolio
class BondPortfolio:
    def __init__(self):
        self.bonds = {}

    @log_execution
    def add_bond(self, bond, quantity, purchase_price):
        """Dodaj obligację do portfela wraz z ilością i ceną nabycia."""
        if bond not in self.bonds:
            # Tworzymy nową listę transakcji dla obligacji
            self.bonds[bond] = []

        # Dodajemy nową transakcję do listy
        self.bonds[bond].append((quantity, purchase_price))

    def get_total_bonds(self, bond):
        """Zwraca łączną liczbę obligacji w portfelu na podstawie wolumenu."""
        total_bonds = 0
        if bond in self.bonds:
            # Suma liczby obligacji w portfelu
            for quantity, _ in self.bonds[bond]:
                total_bonds += quantity
        return total_bonds

    @log_execution
    def total_value(self):
        """Oblicza całkowitą wartość portfela."""
        total = 0
        for bond, transactions in self.bonds.items():
            for quantity, _ in transactions:  # Iteruj po każdej transakcji
                try:
                    kurs_odniesienia = float(bond.kurs_odniesienia)
                    total += kurs_odniesienia * int(quantity) * bond.nominal_value /100
                except ValueError:
                    raise TypeError(
                        f"Kurs odniesienia dla obligacji {bond.nazwa} nie jest liczbą: {bond.kurs_odniesienia}")
        return total
    @log_execution
    def average_interest_rate(self):
        """Oblicz średnie bieżące oprocentowanie portfela, biorąc pod uwagę nominalne oprocentowanie obligacji."""
        total_value = 0
        weighted_rate = 0
        for bond, quantity_data in self.bonds.items():
            for quantity, _ in quantity_data:
                total_value += bond.nominal_value * quantity
                weighted_rate += bond.current_interest * bond.nominal_value * quantity
        return round(weighted_rate / total_value, 2) if total_value > 0 else 0

    @log_execution
    def compare_bond_values(self, bond, purchase_price, quantity):
        """Porównuje wartość obligacji w momencie zakupu i obecnie."""
        bond = next((b for b in self.bonds if b.nazwa == bond.nazwa), None)
        if not bond:
            return f"Obligacja {bond.nazwa} nie znaleziona."

        current_value = bond.kurs_ostatni/100 * quantity * bond.nominal_value
        purchase_value = purchase_price/100 * quantity * bond.nominal_value
        return {
            "nazwa": bond.nazwa,
            "wartość_zakupu": purchase_value,
            "wartość_aktualna": current_value,
            "różnica": current_value - purchase_value
        }

    @log_execution
    def evaluate_diversification(self):
        """
        Ocena dywersyfikacji portfela obligacji.
        Kryteria:
        - Typ oprocentowania (stałe, zmienne: WIBOR3M, WIBOR6M)
        - Liczba unikalnych emitentów
        - Zróżnicowanie typów działalności emitentów
        - Udział największej obligacji w portfelu
        """
        if not self.bonds:
            return "Portfel jest pusty. Brak możliwości oceny dywersyfikacji."

        # Zbieranie danych
        total_value = self.total_value()
        emitents = set()  # Unikalne spółki emitujące obligacje
        sectors = set()  # Typy działalności spółek
        interest_types = set()  # Unikalne typy oprocentowania
        bond_contributions = {}  # Udział poszczególnych obligacji w całym portfelu

        for bond, transactions in self.bonds.items():
            bond_value = sum(quantity * bond.nominal_value for quantity, _ in transactions)
            bond_contributions[bond.nazwa] = bond_value / total_value
            emitents.add(bond.emitent)
            sectors.add(bond.typ_dzialalnosci)

            # Liczenie unikalnych typów oprocentowania
            interest_types.add(bond.interest_type)

        # Obliczanie wskaźników
        num_emitents = len(emitents)
        num_sectors = len(sectors)
        max_bond_contribution = max(bond_contributions.values()) * 100  # Największa obligacja jako % portfela
        interest_type_diversification = len(interest_types)  # Liczymy unikalne typy oprocentowania

        # Ocena dywersyfikacji
        diversification_score = 1
        if num_emitents >= 5:
            diversification_score += 1
        if num_sectors >= 3:
            diversification_score += 1
        if max_bond_contribution <= 20:  # Udział pojedynczej obligacji ≤ 20%
            diversification_score += 1
        if interest_type_diversification >= 2:  # Różnorodność typów oprocentowania
            diversification_score += 1

        # Podsumowanie wyników
        summary = {
            "Liczba emitentów": num_emitents,
            "Liczba sektorów": num_sectors,
            "Największy udział obligacji (%)": round(max_bond_contribution, 2),
            "Różnorodność typów oprocentowania": interest_type_diversification,
            "Ocena dywersyfikacji (1-5)": diversification_score,
        }
        return summary

    @log_execution
    def rank_bonds(self, criterion = "ytm", reverse = True):
        """
        Tworzy ranking obligacji na podstawie określonego kryterium.

        :param criterion: Kryterium rankingu, np. 'ytm' (Yield to Maturity), 'current_interest', 'maturity_date'.
        :param reverse: Jeśli True, sortuje malejąco (najlepsze na górze).
        :return: Posortowana lista słowników zawierających szczegóły obligacji.
        """
        ranking = []
        for bond, transactions in self.bonds.items():
            for quantity, purchase_price in transactions:
                bond_data = {
                    "Nazwa": bond.nazwa,
                    "Emitent": bond.emitent,
                    "Wartość nominalna": bond.nominal_value,
                    "Ilość": quantity,
                    "Cena zakupu": purchase_price,
                    "Typ oprocentowania": bond.interest_type,
                    "YTM (%)": bond.ytm_brutto(purchase_price) if hasattr(bond, "ytm_brutto") else None,
                    "Obecne oprocentowanie (%)": bond.current_interest,
                    "Data zapadalności": bond.maturity_date
                }
                ranking.append(bond_data)

        # Sortowanie według wybranego kryterium
        ranking = sorted(ranking, key = lambda x: x.get(criterion), reverse = reverse)
        return ranking

    @log_execution
    def generate_alerts(self):
        """
        Generuje alerty dla obligacji w portfelu:
        - Jeśli termin wykupu obligacji jest bliski (miesiąc przed datą zapadalności).
        - Jeśli zbliża się termin wypłaty kuponu (miesiąc przed datą wypłaty).

        :return: Lista alertów.
        """
        alerts = []
        current_date = datetime.today().date()
        days_to_maturity = 30
        days_to_coupon = 30

        for bond, transactions in self.bonds.items():
            # Sprawdzenie terminu zapadalności
            if bond.maturity_date:
                days_to_maturity_left = (bond.maturity_date - current_date).days
                if days_to_maturity_left <= days_to_maturity:
                    alerts.append(
                        f"Obligacja '{bond.nazwa}' zapada za {days_to_maturity_left} dni (termin: {bond.maturity_date})."
                    )

            # Sprawdzenie terminów kuponów
            if hasattr(bond, "generate_coupon_dates") and callable(bond.generate_coupon_dates):
                try:
                    coupon_dates = bond.generate_coupon_dates()
                    for date in coupon_dates:
                        days_to_coupon_left = (date - current_date).days
                        if 0 < days_to_coupon_left <= days_to_coupon:
                            alerts.append(
                                f"Zbliża się termin wypłaty kuponu dla '{bond.nazwa}' za {days_to_coupon_left} dni (termin: {date})."
                            )
                except ValueError:
                    alerts.append(f"Nie można obliczyć dat kuponowych dla obligacji '{bond.nazwa}'.")

        return alerts

    @log_execution
    def load_from_xlsx(self, file_name):
        """Załaduj dane z pliku Excel do portfela."""
        try:
            df = pd.read_excel(file_name)
            for index, row in df.iterrows():
                self.add_bond(row['name'], row['quantity'], row['purchase_price'])
        except FileNotFoundError:
            st.warning("Plik z portfelem obligacji nie został znaleziony. Portfolio jest zatem puste.")
