import streamlit as st
import pandas as pd
import plotly.express as px
from bond_scraper import BondScraper
from bond_classes import Bond, BondPortfolio, FixedRateBond, FloatingRateBond
from datetime import date, datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from theme_settings import apply_theme, generate_color_palette

# Inicjalizacja obiektu klasy BondScraper
scraper = BondScraper()

# Wczytanie pliku Excel
file_path = 'portfolio_obligacje.xlsx'
df_portfolio = pd.read_excel(file_path)
bond_portfolio_names = df_portfolio['nazwa'].dropna().unique()
# Tworzenie słownika {nazwa: quantity}
portfolio_dict = df_portfolio[['nazwa', 'wolumen', 'cena_nabycia']].to_dict('records')
myportfolio = BondPortfolio()


# Funkcja do zapisywania do pliku Excel
def add_to_portfolio_xlsx(file_name, bond_name, corp_type, purchase_price, quantity):
    try:
        # Wczytanie istniejącego pliku Excel (jeśli istnieje)
        df = pd.read_excel(file_name)
    except FileNotFoundError:
        # Tworzenie nowego DataFrame, jeśli plik nie istnieje
        df = pd.DataFrame(columns = ['name', 'typ działalności', 'cena_nabycia', 'wolumen', 'data_dodania_obligacji'])

    # Dodanie nowej obligacji
    new_bond = pd.DataFrame([{
        'nazwa': bond_name,
        'typ działalności': corp_type,
        'cena_nabycia': purchase_price,
        'wolumen': quantity,
        'data_dodania_obligacji': datetime.now().strftime('%Y-%m-%d')
    }])

    # Łączenie z istniejącym DataFrame
    df = pd.concat([df, new_bond], ignore_index = True)

    # Zapisanie do pliku Excel
    df.to_excel(file_name, index = False)


# Funkcja zapisu daty danych
def save_data_with_date(df, filename):
    date_info = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df['data pobrania'] = date_info
    df.to_excel(filename + '.xlsx', index = False)
    df.to_csv(filename + '.csv', index = False)
    return date_info


# Mapowanie Interest Type na odpowiednie klasy
interest_type_map = {
    "stałe": FixedRateBond,
    "zmienne": FloatingRateBond
}

# Funkcja do dynamicznego tworzenia obiektów
# Lista przechowująca wszystkie utworzone instancje obligacji
all_bonds = []


def create_bond_instance(details):
    # Ładujemy dane z plików Excel
    df_bonds = pd.read_excel('corporate_bonds.xlsx')
    df_types = pd.read_excel('corp_type.xlsx')

    # Łączenie danych na podstawie kolumny 'nazwa'
    df_merged = pd.merge(df_bonds, df_types, on = 'emitent', how = 'left')

    # Grupowanie danych na podstawie nazwy obligacji
    bonds_info_dict = df_merged.groupby('nazwa').apply(lambda x: x.to_dict(orient = 'records')).to_dict()

    # Uzyskujemy nazwę obligacji z danych wejściowych
    bond_name = details.get("Bond Name")

    # Przypisujemy dane z pliku na podstawie nazwy obligacji
    bond_info = bonds_info_dict.get(bond_name, [{}])[0]  # Pobieramy pierwszą grupę, jeśli jest więcej niż jedna

    # Jeśli nie znaleziono informacji, przypisujemy domyślne wartości
    emitent = bond_info.get('emitent')
    bond_type = bond_info.get('typ działalności', 'bd')
    kurs_otwarcia = bond_info.get('kurs otwarcia', 0)
    kurs_odniesienia = bond_info.get('kurs odniesienia**', 0)
    kurs_ostatni = bond_info.get('kurs ostatni*', 0)
    data_ostatniej_transakcji = bond_info.get('data/czas ost. trans.', 'bd')
    kurs_min = bond_info.get('kurs min', 0)
    kurs_max = bond_info.get('kurs max', 0)
    najlepsza_oferta_kupna_limit = bond_info.get('najlepsza oferta kupna limit', 'bd'),
    najlepsza_oferta_kupna_wolumen = bond_info.get('najlepsza oferta kupna wolumen', 'bd'),
    najlepsza_oferta_sprzedazy_limit = bond_info.get('najlepsza oferta sprzedaży limit', 'bd'),
    najlepsza_oferta_sprzedazy_wolumen = bond_info.get('najlepsza oferta sprzedaży wolumen', 'bd'),
    zmiana = bond_info.get('zmiana', 0)
    wolumen = bond_info.get('wolumen', 0)
    obrot = bond_info.get('obrot', 0)

    reference_rate_dict = {"WIBOR3M": 5.82, "WIBOR6M": 5.8}
    bond_class = interest_type_map.get(details.get("Interest Type"), Bond)
    model_of_forecast = details.get("Model of forecast")
    reference_rate_model = reference_rate_dict.get(model_of_forecast, None) if model_of_forecast else None

    # Tworzymy instancję obligacji
    new_bond = bond_class(
        emitent = emitent,
        nazwa = bond_name,
        segment = "Corporate",
        kurs_otwarcia = kurs_otwarcia,
        kurs_odniesienia = kurs_odniesienia,
        kurs_ostatni = kurs_ostatni,
        data_ostatniej_transakcji = data_ostatniej_transakcji,
        kurs_min = kurs_min,
        kurs_max = kurs_max,
        najlepsza_oferta_kupna_limit = najlepsza_oferta_kupna_limit[0].replace(',', '.'),
        najlepsza_oferta_kupna_wolumen = najlepsza_oferta_kupna_wolumen[0].replace(',', '.'),
        najlepsza_oferta_sprzedazy_limit = najlepsza_oferta_sprzedazy_limit[0].replace(',', '.'),
        najlepsza_oferta_sprzedazy_wolumen = najlepsza_oferta_sprzedazy_wolumen[0].replace(',', '.'),
        zmiana = zmiana,
        wolumen = wolumen,
        obrot = obrot,
        nominal_value = details.get("Nominal Value"),
        maturity_date = details.get("Maturity Date"),
        interest_type = details.get("Interest Type"),
        nominal_margin = details.get("Nominal Margin"),
        current_interest = details.get("Current Period Interest"),
        payments_per_year = details.get("Payments per year"),
        accrued_interest = details.get("Accrued interest"),
        model_of_forecast = details.get("Model of forecast"),
        reference_rate_model = reference_rate_model,
        typ_dzialalnosci = bond_type  # Przypisanie typu działalności
    )

    # Dodanie nowej obligacji do `all_bonds`, jeśli nie istnieje
    if not any(bond.nazwa == bond_name for bond in all_bonds):
        all_bonds.append(new_bond)

    return new_bond


st.set_page_config(layout = "wide")

# Interfejs Streamlit (UI)
st.title("Portfel Obligacji Korporacyjnych Catalyst")


apply_theme()

# Automatyczne uruchomienie skrapowania przy starcie aplikacji
if 'bonds_df' not in st.session_state:
    st.session_state['bonds_df'] = pd.DataFrame()
    st.session_state['data_date'] = None

if st.session_state['bonds_df'].empty:  # Jeśli brak danych w sesji, uruchom skrapowanie
    with st.spinner("Pobieranie ogólnych danych o obligacjach podczas startu aplikacji..."):
        bonds_df = scraper.fetch_bonds()
        if not bonds_df.empty:
            date_info = save_data_with_date(bonds_df, 'general_bond_data')
            st.session_state['bonds_df'] = bonds_df
            st.session_state['data_date'] = date_info
            st.success(f"Dane zostały pomyślnie pobrane podczas startu aplikacji ({date_info}).")
        else:
            st.error("Nie udało się pobrać danych podczas startu aplikacji.")

# Przycisk do aktualizacji danych
if st.button('Aktualizuj dane'):
    with st.spinner("Aktualizowanie ogólnych danych o obligacjach..."):
        bonds_df = scraper.fetch_bonds()
        if not bonds_df.empty:
            date_info = save_data_with_date(bonds_df, 'general_bond_data')
            st.session_state['bonds_df'] = bonds_df
            st.session_state['data_date'] = date_info
            st.success(f"Dane zostały pomyślnie zaktualizowane ({date_info}).")
        else:
            st.error("Nie udało się pobrać danych.")

# Załadowanie istniejących danych, jeśli są zapisane
if 'bonds_df' not in st.session_state:
    st.session_state['bonds_df'] = pd.DataFrame()
    st.session_state['data_date'] = None

# Wczytanie danych z pliku corp_type.xlsx i połączenie z bonds_df
try:
    typ_spolek_df = pd.read_excel('corp_type.xlsx')
    if not st.session_state['bonds_df'].empty:
        bonds_df = st.session_state['bonds_df']
        if 'typ działalności' not in bonds_df.columns:
            bonds_df = bonds_df.merge(typ_spolek_df[['emitent', 'typ działalności']],
                                      on = 'emitent', how = 'left', suffixes = ('_bonds', '_typ'))
        else:
            print("Kolumna 'typ działalności' już istnieje. Merge pominięto.")
        st.session_state['bonds_df'] = bonds_df
except FileNotFoundError:
    st.warning("Plik 'corp_type.xlsx' nie został znaleziony. Proszę go załadować.")

# Wyświetlanie tabeli danych i daty
if not st.session_state['bonds_df'].empty:
    st.write(f"### Notowania obligacji korporacyjnych (stan na dzień {st.session_state['data_date']})")
    bonds_df = st.session_state['bonds_df'].drop(columns = ['Data pobrania'], errors = 'ignore')

    # Skrapowanie danych tylko dla obligacji wpisanych już w portfolio wcześniej
    for bond_name in bonds_df['nazwa']:
        if any(record['nazwa'] == bond_name for record in portfolio_dict):
            # Pobranie szczegółów obligacji
            bond_details = scraper.scrape_details(bond_name)
            bond_instance = create_bond_instance(bond_details)

            # Pobranie ilości i ceny zakupu z portfolio_dict
            record = next(record for record in portfolio_dict if record['nazwa'] == bond_name)
            quantity = record['wolumen']  # Wolumen (ilość)
            purchase_price = record['cena_nabycia']  # Cena zakupu

            # Przypisanie dodatkowych atrybutów do instancji obligacji
            bond_instance.quantity = quantity
            bond_instance.purchase_price = purchase_price

            # Dodanie obligacji do portfela
            myportfolio.add_bond(bond_instance, quantity, purchase_price)
    # Konfiguracja tabeli z AgGrid
    grid_options_builder = GridOptionsBuilder.from_dataframe(bonds_df)
    grid_options_builder.configure_selection('single')

    # Zamrożenie pierwszych dwóch kolumn (jeśli istnieją)
    if len(bonds_df.columns) > 0:
        grid_options_builder.configure_column(bonds_df.columns[0], pinned = "left")
    if len(bonds_df.columns) > 1:
        grid_options_builder.configure_column(bonds_df.columns[1], pinned = "left")

    grid_options = grid_options_builder.build()

    grid_options_builder.configure_pagination(paginationAutoPageSize = True)  # Włączenie paginacji
    grid_options_builder.configure_default_column(editable = False, groupable = False,
                                                  filter = True)  # Włączenie filtrowania
    grid_options_builder.configure_side_bar()  # Pasek boczny z opcjami filtrowania i kolumn


    # Wyświetlenie tabeli z AgGrid
    grid_response = AgGrid(
        bonds_df,
        gridOptions = grid_options,
        use_container_width = True,
        update_mode = GridUpdateMode.MODEL_CHANGED,
        theme='balham',
        height = 700
    )

    # Dodanie zakładek
    tabs = st.tabs(["Wyszukaj obligacje", "Analiza portfela"])

    with tabs[0]:

        # Porównanie kilku obligacji
        st.subheader("Wyszukaj obligacje")

        # Input: lista nazw obligacji
        bond_names_input = st.text_area(
            "Wpisz nazwy obligacji jakich chcesz sprawdzić szczegóły (oddzielone przecinkami):",
            value = st.session_state.get('bond_name_input', '')
        )

        # Przechowywanie danych obligacji w session_state
        if 'bond_details' not in st.session_state:
            st.session_state['bond_details'] = {}

        # Przechowywanie portfela w session_state
        if 'portfolio' not in st.session_state:
            st.session_state['portfolio'] = BondPortfolio()

        if bond_names_input:
            bond_list = [name.strip() for name in bond_names_input.split(",")]

            # Scrapowanie danych tylko dla obligacji wpisanych
            with st.spinner("Ładowanie danych może zająć chwilkę..."):
                for bond_name in bond_list:
                    if bond_name not in st.session_state['bond_details']:
                        bond_data = scraper.scrape_details(bond_name)
                        if bond_data:
                            st.session_state['bond_details'][bond_name] = bond_data

            # Pobranie szczegółów dla wszystkich wybranych obligacji
            bond_details_list = [st.session_state['bond_details'][bond_name] for bond_name in bond_list if
                                 bond_name in st.session_state['bond_details']]

            if bond_details_list:
                st.subheader("Analiza inwestycji")

                for bond_data in bond_details_list:
                    # Utworzenie obiektu obligacji
                    bond = create_bond_instance(bond_data)

                    # Układ z czterema kolumnami
                    col1, col2, col3 = st.columns([1, 1.3, 1.8])

                    # Kolumna 1: Szczegóły obligacji
                    with col1:
                        st.markdown(f"### **{bond.nazwa}**")
                        st.write(f"#### *{bond.typ_dzialalnosci}*\n")
                        st.write(f"**Wartość nominalna:** {bond.nominal_value} PLN")
                        st.write(f"**Typ oprocentowania:** {bond.interest_type}")
                        st.write(f"**Oprocentowanie:** {bond.nominal_margin}")
                        st.write(f"**Narosłe odsetki:** {bond.accrued_interest}")
                        st.write(f"**Wartość Kuponu:** {bond.calculate_coupon()} PLN")
                        st.write(f"**Lata do wykupu:** {bond.years_to_maturity(date.today())}")
                        st.write(f"**Model prognozy:** {bond.model_of_forecast}")

                    # Kolumna 2: Wejścia użytkownika
                    with col2:
                        st.markdown("### Dane rynkowe")
                        colm1, colm2 = st.columns([1, 1])
                        with colm1:
                            st.metric("Ostatni kurs", bond.kurs_ostatni)
                            st.metric("Kurs minimalny", bond.kurs_min)
                            st.write("Najlepsza oferta kupna")
                            st.metric("Limit", bond.najlepsza_oferta_kupna_limit)
                            st.write("Najlepsza oferta sprzedaży")
                            st.metric("Limit", bond.najlepsza_oferta_sprzedazy_limit)
                        with colm2:
                            st.metric("Data ostatniej transakcji", bond.data_ostatniej_transakcji)
                            st.metric("Kurs maksymalny", bond.kurs_max)
                            st.markdown("&#160;")
                            st.metric("Wolumen", bond.najlepsza_oferta_kupna_wolumen)
                            st.markdown("&#160;")
                            st.metric("Wolumen", bond.najlepsza_oferta_sprzedazy_wolumen)

                    # Kolumna 3: Dane wejściowe inwestycji

                    with col3:
                        st.markdown("### Kalkulator rentowności obligacji")
                        col31, col32 = st.columns([1,1])
                        with col31:
                            num_bonds = st.number_input(
                                f"Liczba obligacji do zakupu:",
                                min_value = 1, value = 1, step = 1, key = f"num_{bond.nazwa}"
                            )

                            # Sprawdź, czy kurs_ostatni jest liczbą
                            if isinstance(bond.kurs_ostatni, (int, float)) and not isinstance(bond.kurs_ostatni, bool):
                                domyslna_cena = bond.kurs_ostatni
                            else:
                                domyslna_cena = 100.0

                            cena_nabycia = st.number_input(
                                f"Cena zakupu za obligację:",
                                min_value = 0.0, value = domyslna_cena, step = 0.01, key = f"price_{bond.nazwa}"
                            )

                        with col32:
                            total_investment = num_bonds * cena_nabycia
                            bond_ytm_brutto = bond.ytm_brutto(cena_nabycia)
                            bond_ytm_netto = bond.ytm_netto(cena_nabycia)
                            bond_ekwivalent_ytm_brutto = bond.ekwivalent_ytm_brutto(cena_nabycia)
                            bond_duration_macaulay = bond.macaulay_duration(cena_nabycia)
                            bond_duration_modified = bond.modified_duration(cena_nabycia)

                            st.write(f"**YTM (Brutto):** {bond_ytm_brutto:.2f}%")
                            st.write(f"**YTM (Netto):** {bond_ytm_netto:.2f}%")
                            st.write(f"**Ekwiwalent YTM brutto:** {bond_ekwivalent_ytm_brutto:.2f}%")
                            st.write(f"**Czas trwania Macaulay'a (w latach):** {bond_duration_macaulay:.2f}")
                            st.write(f"**Zmodyfikowany czas trwania (w latach):** {bond_duration_modified:.2f}")

                            # Dodanie obligacji do portfela
                            if st.button(f"Dodaj {bond.nazwa} do portfela", key = f"add_{bond.nazwa}"):
                                myportfolio.add_bond(bond, num_bonds, cena_nabycia)
                                add_to_portfolio_xlsx(
                                    'portfolio_obligacje.xlsx',
                                    bond.nazwa,
                                    bond.typ_dzialalnosci,
                                    cena_nabycia,
                                    num_bonds
                                )
                                st.success(f"Dodano {num_bonds} obligacji {bond.nazwa} do portfela.")

                    # Separator pomiędzy obligacjami
                    st.divider()

    with tabs[1]:
        # Inicjalizacja portfela w sesji
        if "portfolio" not in st.session_state:
            st.session_state["portfolio"] = BondPortfolio()
            portfolio = st.session_state["portfolio"]


        # Załaduj dane o typach działalności z pliku Excel
        df_company_types = pd.read_excel('corp_type.xlsx')  # Upewnij się, że plik jest poprawnie załadowany

        # Sprawdzenie, czy w portfelu są obligacje
        if len(myportfolio.bonds) > 0:


            # Generowanie alertów na podstawie stałych progów
            try:
                alerts = myportfolio.generate_alerts()
                if alerts:
                    for alert in alerts:
                        st.write(f"⚠️ {alert}")
            except Exception as e:
                st.error(f"Nie udało się wygenerować alertów: {e}")

            diversification_result = myportfolio.evaluate_diversification()

            # Pobranie wartości według kluczy
            liczba_emitentow = diversification_result["Liczba emitentów"]
            liczba_sektorow = diversification_result["Liczba sektorów"]
            najwiekszy_udzial = diversification_result["Największy udział obligacji (%)"]
            liczba_typow_oprocentowania = diversification_result["Różnorodność typów oprocentowania"]
            ocena_dywersyfikacji = diversification_result["Ocena dywersyfikacji (1-5)"]
            avg_interest = myportfolio.average_interest_rate()
            total_value = myportfolio.total_value()

            col12, col22, col32, col42, col52, col62 = st.columns([1,1,1,1,1,1])

            with col12:
                st.metric("Liczba emitentów", liczba_emitentow)
            with col22:
                st.metric("Największy udział obligacji (%)", f"{najwiekszy_udzial:.2f}%")
            with col32:
                st.metric("Liczba sektorów", liczba_sektorow)
            with col42:
                st.metric("Różnorodność typów oprocentowania", liczba_typow_oprocentowania)
            with col52:
                st.metric("Średnie oprocentowanie portfela", avg_interest)
            with col62:
                st.metric("Całkowita wartość portfela", total_value)

            if ocena_dywersyfikacji < 3:
                color = "#fa5568"
            elif ocena_dywersyfikacji == 3:
                color = "#f1ff54"
            else:
                color = "#bef299"

            # Przedstawienie oceny dywersyfikacji w większym formacie z odpowiednim kolorem
            st.markdown(
                f"<h1 style='color:{color}; text-align: center;'>Ocena dywersyfikacji (1-5): {ocena_dywersyfikacji}</h1>",
                unsafe_allow_html = True
            )

            if najwiekszy_udzial > 15:
                st.warning("Zbyt duży udział jednej obligacji! Rozważ dodanie obligacji innych emitentów.")
            if liczba_sektorow < 3:
                st.warning("Zbyt mała różnorodność sektorów. Poszukaj obligacji z innych branż.")
            if liczba_typow_oprocentowania < 2:
                st.warning(
                    "Rozważ dywersyfikację typów oprocentowania, np. dodanie obligacji o stałym oprocentowaniu.")

            col1, col2 = st.columns([1,5])

            with col1:
                st.subheader("Obligacje w portfelu")
                # Iteracja po obligacjach w portfelu
                for bond in myportfolio.bonds:
                    with st.expander(f"{bond.nazwa}"):  # Nagłówek expandera z nazwą obligacji
                        # Szczegóły obligacji
                        st.write(f"Emitent: {bond.emitent}")
                        st.write(f"Oprocentowanie: {bond.current_interest}% ({bond.interest_type})")
                        st.write(f"Data zapadalności: {bond.maturity_date}")
                        st.write(f"Wartość nominalna: {bond.nominal_value}")
                        st.write(f"Cena nabycia: {bond.purchase_price}")
                        st.write(f"Ilość obligacji: {bond.quantity}")
                        st.write(f"Wartość nabycia: {bond.quantity*bond.purchase_price*bond.nominal_value/100}")
                        st.metric("Obecna cena rynkowa:", bond.quantity*bond.kurs_odniesienia*bond.nominal_value/100, delta=bond.quantity*bond.kurs_odniesienia*bond.nominal_value/100 - bond.quantity*bond.purchase_price*bond.nominal_value/100)

            with col2:

                # Sekcja rankingów obligacji
                st.subheader("Ranking obligacji w portfelu")

                # Wybór kryterium rankingu
                criteria = {
                    "YTM": "YTM (%)",
                    "Obecne oprocentowanie": "Obecne oprocentowanie (%)",
                    "Data zapadalności": "Data zapadalności"
                }

                selected_criterion = st.selectbox(
                    "Wybierz kryterium rankingu:",
                    list(criteria.keys()),
                    index = 0
                )

                # Generowanie rankingu
                try:
                    ranked_bonds = myportfolio.rank_bonds(criterion = criteria[selected_criterion])
                    df = pd.DataFrame(ranked_bonds)
                    AgGrid(df, fit_columns_on_grid_load = True)
                except Exception as e:
                    st.error(f"Nie udało się wygenerować rankingu: {e}")


                all_coupons = []  # Lista na dane kuponowe
                for bond in myportfolio.bonds:
                    try:
                        # Pobierz daty kuponów i ich wartości
                        coupon_dates = bond.generate_coupon_dates()
                        coupon_values = [bond.calculate_coupon()] * len(coupon_dates)

                        # Tworzenie DataFrame dla obligacji
                        bond_data = pd.DataFrame({
                            "Data": coupon_dates,
                            "Wartość kuponu": coupon_values,
                            "Obligacja": bond.nazwa
                        })
                        all_coupons.append(bond_data)
                    except ValueError as e:
                        st.warning(f"Nie udało się wygenerować danych kuponowych dla obligacji {bond.nazwa}: {e}")

                # Połącz wszystkie dane w jeden DataFrame
                if all_coupons:
                    coupon_data = pd.concat(all_coupons, ignore_index = True)
                    coupon_data["Data"] = pd.to_datetime(
                        coupon_data["Data"])  # Upewnij się, że kolumna Data jest w formacie datetime

                    # Dodanie kolumny "Miesiąc" i grupowanie danych
                    coupon_data["Miesiąc"] = coupon_data["Data"].dt.to_period("M").dt.to_timestamp()
                    # Grupowanie danych według "Miesiąc" i "Obligacja", sumowanie tylko kolumny "Wartość kuponu"
                    grouped_coupons = coupon_data.groupby(["Miesiąc", "Obligacja"], as_index = False)[
                        "Wartość kuponu"].sum()

                    # Tworzenie wykresu skumulowanego słupkowego
                    fig = px.bar(
                        grouped_coupons,
                        x = "Miesiąc",
                        y = "Wartość kuponu",
                        color = "Obligacja",
                        title = "Skumulowane wartości kuponów według miesięcy",
                        labels = {"Miesiąc": "Miesiąc", "Wartość kuponu": "Wartość kuponu (PLN)",
                                  "Obligacja": "Nazwa obligacji"},
                        barmode = "stack"  # Skumulowane słupki
                    )
                    fig.update_layout(
                        title_font = dict(family = "Poppins", size = 18),
                        font = dict(family = "Poppins", size = 14),
                        legend = dict(bgcolor = "rgba(0,0,0,0)")
                    )
                    st.plotly_chart(fig)
                else:
                    st.warning("Brak danych kuponowych dla obligacji w portfelu.")




                # Tworzenie listy dla interest_type i model_of_forecast na podstawie liczby obligacji w portfelu
                data = []
                for bond in myportfolio.bonds:
                    total_bonds = myportfolio.get_total_bonds(bond)  # Uzyskujemy liczbę obligacji z portfela
                    for _ in range(total_bonds):  # Dodajemy każdą obligację tyle razy, ile jej w portfelu
                        data.append({
                            "interest_type": bond.interest_type,
                            "model_of_forecast": bond.model_of_forecast if bond.interest_type == "zmienne" else ""
                        })

                # Konwersja do DataFrame
                df = pd.DataFrame(data)

                # Mapa kolorów
                color_palette = generate_color_palette()['small_palette']

                # Wykres sunburst
                fig_sunburst = px.sunburst(
                    df,
                    path=["interest_type", "model_of_forecast"],
                    title="Struktura portfela według typu oprocentowania i modelu prognozy",
                    color="interest_type",
                    color_discrete_sequence=color_palette,  # Użycie mapy kolorów
                )

                # Ustawienia czcionki i transparentne tło legendy
                fig_sunburst.update_layout(
                    title_font=dict(family="Poppins", size=18),  # Czcionka dla tytułów
                    font=dict(family="Poppins", size=14),  # Czcionka wykresów
                    legend=dict(bgcolor="rgba(0,0,0,0)")  # Przezroczyste tło legendy
                )

                fig_sunburst.update_traces(
                    hovertemplate="<b>Oprocentowanie %{id}</b><br>Liczba obligacji:%{value}<br>Procentowy udział w portfelu: %{percentEntry}<br>",
                    hoverlabel=dict(font_size=12, font_family="Poppins")
                )

                # Wykres działalności
                activity_types = [bond.typ_dzialalnosci for bond in myportfolio.bonds for _ in range(myportfolio.get_total_bonds(bond))]  # Uwzględniamy wolumen
                activity_counts = pd.Series(activity_types).value_counts()

                # Procentowy podział według typu działalności
                fig_activity = px.pie(
                    names=activity_counts.index,
                    values=activity_counts.values,
                    title="Podział portfela według typu działalności",
                    hole=0.5,
                    color_discrete_sequence=color_palette  # Użycie mapy kolorów
                )

                # Ustawienia czcionki i transparentne tło legendy
                fig_activity.update_layout(
                    title_font=dict(family="Poppins", size=18),  # Czcionka dla tytułów
                    font=dict(family="Poppins", size=14),  # Czcionka wykresów
                    legend=dict(bgcolor="rgba(0,0,0,0)")  # Przezroczyste tło legendy
                )

                fig_activity.update_traces(
                    hovertemplate="<b>%{label}</b><br>Liczba obligacji: %{value}</br>",
                    hoverlabel=dict(font_size=12, font_family="Poppins")
                )

                # Rozkład dat zapadalności
                maturity_dates = [
                    bond.maturity_date for bond in myportfolio.bonds
                    for _ in range(myportfolio.get_total_bonds(bond))
                ]  # Lista dat zapadalności uwzględniająca wolumen

                # Rodzaj oprocentowania (stałe/zmienne)
                interest_types = [
                    bond.interest_type for bond in myportfolio.bonds
                    for _ in range(myportfolio.get_total_bonds(bond))
                ]  # Uwzględnienie rodzaju oprocentowania dla każdej obligacji

                # Konwersja na DataFrame i dodanie roku zapadalności oraz rodzaju oprocentowania
                maturity_df = pd.DataFrame({
                    'Data zapadalności': pd.to_datetime(maturity_dates),
                    'Rodzaj oprocentowania': interest_types
                })
                maturity_df['Rok zapadalności'] = maturity_df['Data zapadalności'].dt.year

                # Dynamiczny histogram z interwałami czasowymi i podziałem na rodzaj oprocentowania
                fig_maturity = px.histogram(
                    maturity_df,
                    x = 'Data zapadalności',
                    color = 'Rodzaj oprocentowania',  # Podział na stałe i zmienne oprocentowanie
                    title = "Rozkład dat zapadalności obligacji",
                    labels = {'x': 'Data zapadalności', 'y': 'Liczba obligacji'},
                    color_discrete_map = {'stałe': generate_color_palette()['middle'], 'zmienne': generate_color_palette()['title']},  # Przypisanie kolorów
                    nbins = 20  # Liczba binów do podziału na przedziały
                )

                # Dostosowanie wykresu
                fig_maturity.update_layout(
                    title_font = dict(family = "Poppins", size = 18),  # Czcionka dla tytułu
                    font = dict(family = "Poppins", size = 14),  # Czcionka wykresów
                    xaxis_title = "Data zapadalności",
                    yaxis_title = "Liczba obligacji",
                    legend = dict(bgcolor = "rgba(0,0,0,0)")  # Przezroczyste tło legendy
                )

                # Dodanie tekstu dla zakresów
                fig_maturity.update_traces(
                    hovertemplate="<b>Data zapadalności:</b> %{x|%Y-%m-%d}<br><b>Liczba obligacji:</b> %{y}<br>"
                )

                # Wyświetlenie wykresów w układzie obok siebie
                col1, col2 = st.columns(2)

                with col1:
                    st.plotly_chart(fig_sunburst)

                with col2:
                    st.plotly_chart(fig_activity)

                # Rozkład dat zapadalności obligacji
                st.plotly_chart(fig_maturity)
        else:
            st.warning("Twój portfel jest pusty. Dodaj obligacje, aby zobaczyć analizę.")