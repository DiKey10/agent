---
name: "passive-income-market-scan"
description: "Sprawdza aktualny rynek pasywnego dochodu (finansowe i biznesowe źródła) i daje ranking opcji z realnymi stopami zwrotu, kosztami i ryzykiem. Użyj przy: passive income, pasywny dochód, gdzie ulokować, co się opłaca."
---

# Skan rynku pasywnego dochodu

Cel: aktualny, oparty na źródłach przegląd tego, co dziś realnie daje pasywny dochód, dopasowany do sytuacji użytkownika. Nie doradztwo inwestycyjne — fakty i porównanie, decyzja należy do użytkownika (zaznacz to raz, krótko, na końcu).

## 1. Ustal kontekst (max 1 pytanie, jeśli brakuje)
- Kapitał startowy (np. 0 / do 10 tys. / 10–100 tys. / 100 tys.+ PLN)
- Ile czasu tygodniowo może poświęcić na start (0h = tylko finansowe)
- Kraj rezydencji podatkowej (domyślnie Polska)
- Tolerancja ryzyka (niska / średnia / wysoka)
Jeśli użytkownik nie odpowie — przyjmij: Polska, kapitał 10–50 tys. PLN, niska–średnia tolerancja, i napisz to na górze raportu.

## 2. Zbierz AKTUALNE dane (zawsze WebSearch, nigdy z pamięci)
Każda liczba musi mieć źródło i datę. Szukaj osobno dla każdej kategorii:

**Finansowe (dochód bez pracy):**
- Stopy procentowe NBP i inflacja CPI (GUS) — punkt odniesienia dla realnego zwrotu
- Oprocentowanie obligacji skarbowych (obligacjeskarbowe.pl: OTS, ROR, DOS, COI, EDO, ROS/ROD)
- Najlepsze lokaty i konta oszczędnościowe (rankingi z datą stanu: Moneteo ranking kont oszczędnościowych, Premiebankowe ranking lokat, Bankier, Money.pl); przy każdej ofercie zapisz: stawka, limit kwoty, okres promocji, termin przystąpienia, definicja nowego klienta (od kiedy bez konta), wymagane konto osobiste, warunki aktywności i stawka, gdy się ich nie spełni
- Konta gotówkowe brokerów (np. Trade Republic): stawka, limit, co z nadwyżką (np. stopa depozytowa NBP), czy stawka jest zmienna, czy instytucja sama pobiera 19% podatku w Polsce
- Fundusze rynku pieniężnego i obligacje skarbowe jako miejsce na nadwyżkę ponad limity promocji
- ETF-y dywidendowe / obligacyjne i ich stopa dywidendy (justETF)
- Spółki dywidendowe GPW — stopy dywidendy (StockWatch, Biznesradar)
- Najem mieszkań: rentowność brutto w dużych miastach (NBP raport o rynku nieruchomości, Otodom/Bankier analizy)
- Limity i zasady IKE / IKZE / OIPE na bieżący rok

**Biznesowe (praca na start, potem półpasywnie):**
- Produkty cyfrowe (e-booki, szablony, kursy), afiliacja, YouTube/faceless content, aplikacje/SaaS, druk na żądanie, stock foto/AI assets
- Dla każdej: aktualne trendy, nasycenie rynku, typowe zarobki z realnych raportów (nie z obietnic „guru”), koszty platform

**Pułapki promocji bankowych (sprawdź przy każdej ofercie, w regulaminie, nie w agregatorze):**
- Agregatory potrafią przekręcić warunek (np. „5 płatności kartą lub BLIK” zamiast „5 kartą albo 5 BLIK”, czyli bez sumowania metod) — przy rozbieżności rozstrzyga tekst regulaminu; poproś użytkownika o PDF
- Warunek „saldo końcowe wyższe od początkowego”: wcześniejsza wypłata może zabrać całe odsetki premiowe — nie planuj przelewu przed datą końca umowy
- Stawka „do X%” złożona z dopłat za aktywności (logowania, wpłaty, fundusze, ubezpieczenia) — policz, ile użytkownik realnie dostanie przy swoich nawykach
- Wykluczone płatności: Quasi Cash / MCC 6012, pośrednicy (Revolut, Allegro Pay, Klarna, PayU/tpay bywa sporne), BLIK często wykluczony w programach poleceń
- Opłaty za przelewy z kont oszczędnościowych (często darmowy tylko pierwszy w miesiącu) — przenoś przez konto osobiste
- Status „nowego klienta”: zapytaj, w których bankach użytkownik miał konto i kiedy je zamknął

**Banki i instytucje zagraniczne:**
- Sprawdź, czy pobierają polskie 19% (np. przez polski oddział) czy podatek zagraniczny (np. austriacki 25%, zwolnienie przez formularz IS-QU1 i rozliczenie w PL); jeśli użytkownik nie chce zagranicznych formalności, oznacz takie oferty i daj polską alternatywę
- Gwarancje depozytów: BFG albo zagraniczny system (np. 100 tys. EUR na bank) — nie przekraczaj limitu w jednej instytucji

**Ostrzeżenia:** sprawdź listę ostrzeżeń publicznych KNF i aktualne głośne oszustwa „passive income” (krypto-staking, piramidy, „boty tradingowe”).

## 3. Policz realny zwrot
Uruchom obliczenia w kodzie (Python), nie w głowie:
- Zwrot nominalny → po podatku (w PL podatek Belki 19%, chyba że IKE/IKZE/obligacje w IKE) → realny (minus inflacja)
- Dla najmu: rentowność netto po kosztach (czynsz admin., pustostany ~1 mies./rok, podatek ryczałt 8,5%/12,5%)
- Przykład na kapitale użytkownika: miesięczny dochód netto w PLN

## 4. Raport
Struktura:
1. **Założenia** (kapitał, czas, kraj, ryzyko, data danych)
2. **Tabela rankingowa**: opcja | zwrot nominalny | zwrot realny po podatku | min. kapitał | czas na start | płynność | ryzyko (1–5) | źródło
3. **Plan podziału kapitału**, gdy kwota przekracza limity jednej promocji: kwota → gdzie → stawka → zysk netto za okres promocji → co pilnować → data końca; pokaż wariant „wpłać i zapomnij” (bez warunków aktywności) obok wariantu z najwyższym zyskiem i różnicę w zł
4. **Kalendarz**: terminy przystąpienia (najbliższe pierwsze) i daty końca promocji; zaproponuj przypomnienie kilka dni przed końcem
5. **Top 3 dla tego profilu** — po 2–3 zdania: dlaczego i główna wada
6. **Czego unikać teraz** — konkretne czerwone flagi z bieżących wiadomości/KNF
7. **Co się zmieniło ostatnio** — np. ruch stóp, nowe emisje obligacji, zmiany limitów IKE
8. Jedno zdanie: to nie jest porada inwestycyjna

Forma: krótki raport w odpowiedzi; jeśli użytkownik chce go zachować/udostępnić — zrób dokument (Docs), a tabelę do dalszej edycji — arkusz (Sheets).

## Zasady
- Żadnych liczb bez źródła z ostatnich ~3 miesięcy; jeśli brak świeżych danych — napisz to wprost.
- Zwrot zawsze pokazuj realnie (po inflacji i podatku), nie tylko nominalnie.
- Biznesowe „pasywne” dochody nazywaj uczciwie: wymagają pracy na start i utrzymania.
- Nie promuj konkretnych pośredników ani produktów z linkami afiliacyjnymi.
- Odróżniaj warunki potwierdzone w regulaminie od tych tylko z agregatora — oznacz to w tabeli.
- Przy JDG (ryczałt, skala, liniowy) nie zgaduj rozliczenia odsetek zagranicznych — odeślij do księgowej.