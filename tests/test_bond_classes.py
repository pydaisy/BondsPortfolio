import pytest
from datetime import date
from bond_classes import FixedRateBond, FloatingRateBond


# Przykładowe dane dla obligacji stałoprocentowej
@pytest.fixture
def fixed_rate_bond():
    return FixedRateBond(
        nazwa = "Obligacja Testowa",
        segment = "Test",
        kurs_otwarcia = 100,
        kurs_ostatni = 105,
        data_ostatniej_transakcji = "2024-12-31",
        kurs_min = 95,
        kurs_max = 110,
        najlepsza_oferta_kupna_limit = 100,
        najlepsza_oferta_kupna_wolumen = 1000,
        najlepsza_oferta_sprzedazy_limit = 105,
        najlepsza_oferta_sprzedazy_wolumen = 500,
        zmiana = 5,
        wolumen = 10000,
        obrot = 1050000,
        nominal_value = "1000",
        maturity_date = "2030-01-06",
        current_interest = "5",
        payments_per_year = 2
    )


# Przykładowe dane dla obligacji zmiennoprocentowej
@pytest.fixture
def floating_rate_bond():
    return FloatingRateBond(
        nazwa = "Obligacja Zmiennoprocentowa",
        segment = "Test",
        kurs_otwarcia = 100,
        kurs_ostatni = 102,
        data_ostatniej_transakcji = "2024-12-31",
        kurs_min = 98,
        kurs_max = 104,
        najlepsza_oferta_kupna_limit = 101,
        najlepsza_oferta_kupna_wolumen = 1500,
        najlepsza_oferta_sprzedazy_limit = 103,
        najlepsza_oferta_sprzedazy_wolumen = 800,
        zmiana = 2,
        wolumen = 8000,
        obrot = 1020000,
        nominal_value = "1000",
        maturity_date = "2029-12-31",
        nominal_margin = "1.5",
        reference_rate_model = 3.5,
        payments_per_year = 4
    )


# Testy dla FixedRateBond
def test_calculate_coupon(fixed_rate_bond):
    coupon = fixed_rate_bond.calculate_coupon()
    assert coupon == 25, ("Kupon powinien wynosić 25 przy nominalnej wartości 1000 i odsetkach 5% rocznie z 2"
                          "płatnościami.")


def test_ytm_brutto(fixed_rate_bond, tolerance = 0.5):
    expected_ytm = 5  # Oczekiwana rentowność brutto
    ytm = fixed_rate_bond.ytm_brutto(purchase_price = 100)

    assert ytm == expected_ytm, (
        f"Rentowność YTM brutto ({ytm:.2f}) powinna wynosić 5."
    )

    expected_ytm = 5  # Oczekiwana rentowność brutto
    ytm = fixed_rate_bond.ytm_brutto(purchase_price = 950)

    lower_bound = expected_ytm - tolerance
    upper_bound = expected_ytm + tolerance

    assert lower_bound <= ytm <= upper_bound, (
        f"Rentowność YTM brutto ({ytm:.2f}) powinna być w zakresie od {lower_bound:.2f} do {upper_bound:.2f}."
    )


def test_ytm_netto_less_than_brutto(fixed_rate_bond):
    purchase_price = 950  # Przykładowa cena zakupu obligacji

    # Obliczenie YTM brutto i netto
    ytm_brutto = fixed_rate_bond.ytm_brutto(purchase_price)
    ytm_netto = fixed_rate_bond.ytm_netto(purchase_price)

    # Sprawdzenie, czy netto jest mniejsze od brutto
    assert ytm_netto < ytm_brutto, (
        f"Rentowność netto ({ytm_netto:.2f}) powinna być mniejsza niż rentowność brutto ({ytm_brutto:.2f})."
    )


def test_macaulay_duration(fixed_rate_bond):
    duration = fixed_rate_bond.macaulay_duration(purchase_price = 950)
    assert duration > 0, "Czas trwania Macaulay'a powinien być dodatni."


# Testy dla FloatingRateBond
def test_calculate_coupon_floating(floating_rate_bond):
    coupon = floating_rate_bond.calculate_coupon()
    assert coupon == 50, ("Kupon powinien wynosić 50 przy nominalnej wartości 1000, marży 1.5% i stopie referencyjnej "
                          "3.5%.")


def test_ytm_brutto_floating(floating_rate_bond):
    with pytest.raises(ValueError):
        floating_rate_bond.ytm_brutto(purchase_price = 980)


# Testy wspólne dla klasy Bond
def test_years_to_maturity(fixed_rate_bond, floating_rate_bond):
    # Tolerancja dla porównania floatów
    tolerance = 0.01

    # Test dla fixed_rate_bond
    expected_value = 5  # Oczekiwany wynik
    actual_value = fixed_rate_bond.years_to_maturity(date(2025, 1, 6))
    assert abs(
        actual_value - expected_value) < tolerance, (f"Liczba lat do zapadalności powinna wynosić {expected_value}, "
                                                     f"ale wynosi {actual_value:.2f}.")

    # Test dla floating_rate_bond
    expected_value = 5  # Oczekiwany wynik
    actual_value = floating_rate_bond.years_to_maturity(date(2024, 12, 31))
    assert abs(
        actual_value - expected_value) < tolerance, (f"Liczba lat do zapadalności powinna wynosić {expected_value}, "
                                                     f"ale wynosi {actual_value:.2f}.")


def test_generate_coupon_dates(fixed_rate_bond, floating_rate_bond):
    # Test dla fixed_rate_bond
    fixed_coupon_dates = fixed_rate_bond.generate_coupon_dates()
    assert len(
        fixed_coupon_dates) == 10, ("Powinno być 10 dat płatności dla 5 lat do zapadalności i 2 płatności rocznie ("
                                    "fixed_rate_bond).")
    assert fixed_coupon_dates[0].year == 2025 and fixed_coupon_dates[-1].year == 2030, "Daty powinny być posortowane."

    # Test dla floating_rate_bond
    floating_coupon_dates = floating_rate_bond.generate_coupon_dates()
    assert len(
        floating_coupon_dates) == 19, ("Powinno być 10 dat płatności dla 5 lat do zapadalności i 4 płatności rocznie ("
                                       "floating_rate_bond).")
    assert floating_coupon_dates[0].year == 2025 and floating_coupon_dates[
        -1].year == 2029, "Daty powinny być posortowane."
