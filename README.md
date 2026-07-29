# Rolki → Przepisy

Wklejasz link do rolki z Instagrama, dostajesz gotowy przepis po polsku — ze
składnikami w gramach, krokami, makro i kadrami z filmu.

Rolki, które nie są o gotowaniu, są automatycznie odrzucane, więc do bazy trafia
tylko to, co da się ugotować.

## Jak to działa

```
link → yt-dlp → ffmpeg ─┬→ audio  → Whisper (lokalnie) → transkrypcja ─┐
                        └→ klatki ───────────────────────────────────┐ │
                           opis posta ────────────────────────────┐  │ │
                                                                  ↓  ↓ ↓
                                                        Claude (structured output)
                                                                  ↓
                                                    przepis po polsku → SQLite
```

Do modelu lecą **wszystkie trzy źródła naraz** i to jest sedno tego rozwiązania:
w rolkach kulinarnych ilości składników są zwykle wypisane tylko na ekranie,
kolejność czynności pada tylko w narracji, a czas i temperatura pieczenia bywają
wyłącznie w opisie posta. Osobno żadne z tych źródeł nie wystarcza.

Odpowiedź modelu jest wymuszona schematem JSON, więc nie ma parsowania tekstu
ani ryzyka, że wróci coś innego niż przepis.

## Instalacja

Potrzebujesz Pythona 3.11+ oraz **ffmpeg** (bez niego nie ma transkrypcji ani
kadrów — aplikacja zadziała, ale na samym opisie posta).

```bash
# ffmpeg
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Ubuntu/Debian

# aplikacja
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[whisper]'     # z lokalną transkrypcją
# pip install -e .              # bez Whispera (mniejsza instalacja)

cp .env.example .env            # i wklej swój klucz ANTHROPIC_API_KEY
```

Klucz wygenerujesz na <https://console.anthropic.com/settings/keys>.

## Uruchomienie

```bash
rolki serve                     # http://127.0.0.1:8000
```

Wklejasz link, pasek pokazuje postęp (pobieram → rozpoznaję mowę → układam
przepis), po chwili przepis pojawia się na liście.

Serwer słucha domyślnie tylko na `127.0.0.1`. Żeby wejść z telefonu w tej samej
sieci Wi-Fi: `rolki serve --host 0.0.0.0` i wejdź na adres IP komputera.

### Z terminala

```bash
rolki add https://www.instagram.com/reel/XXXXXXXXX/
rolki add --file linki.txt      # cała lista po kolei, do nadrabiania zaległości
rolki list
```

## Konfiguracja

Wszystko w `.env` (opis każdej opcji w `.env.example`):

| Zmienna | Domyślnie | Do czego |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Klucz do Claude API (wymagany) |
| `RECIPES_MODEL` | `claude-opus-5` | `claude-sonnet-5` jest tańszy |
| `RECIPES_TRANSCRIBER` | `local` | `none` wyłącza transkrypcję |
| `RECIPES_WHISPER_MODEL` | `small` | `base` szybciej, `medium` dokładniej |
| `RECIPES_FRAME_COUNT` | `6` | Ile klatek analizuje model; `0` wyłącza |
| `RECIPES_DATA_DIR` | `./data` | Baza, cache i pobrane pliki |

## Koszty

Whisper liczy się lokalnie i jest darmowy. Płacisz tylko za jedno zapytanie do
Claude na rolkę — przy 6 klatkach to rząd kilku groszy. Każdy kosztowny krok
(pobranie, transkrypcja, ekstrakcja) jest cache'owany osobno pod ID rolki, więc
ponowne przetworzenie tego samego linku nie kosztuje nic.

Cache leży w `data/cache/`. Jeśli zmienisz prompt i chcesz przeliczyć przepisy
od nowa: `rm -rf data/cache/recipe` (transkrypcje zostaną).

## API

Aplikacja webowa siedzi na zwykłym REST-cie, więc da się ją podpiąć pod skrót
z telefonu albo inny frontend:

```
POST   /api/jobs           {"url": "..."}  → 202 {"job_id": "..."}
GET    /api/jobs/{id}                      → status i postęp
GET    /api/recipes?q=…                    → lista przepisów
GET    /api/recipes/{id}                   → jeden przepis
DELETE /api/recipes/{id}
```

Pełna dokumentacja pod `/docs`.

## Ograniczenia i uwagi

**Tylko linki, które sam wkleisz.** Aplikacja nie loguje się na Twoje konto i nie
przegląda niczego automatycznie. To świadoma decyzja: pobieranie publicznych
postów przez yt-dlp jest stabilne, a scrapowanie z zalogowanego konta łamie
regulamin Instagrama i kończy się blokadą konta. Jeśli kiedyś dojdzie
pobieranie z zapisanych postów, trzeba to zrobić przez oficjalne API Meta.

**Przepisy są odtworzone, nie przepisane.** Model składa je z tego, co widać
i słychać w filmie. Przy niewyraźnej mowie albo szybko przewijanych napisach
ilości mogą się nie zgadzać — przy pierwszym gotowaniu warto zerknąć na
oryginalną rolkę (link jest na stronie przepisu).

**Makro jest szacunkowe**, chyba że autor rolki podał konkretne liczby — wtedy
przepis pokazuje je bez dopisku „szacunkowo".

**Prawa autorskie.** Zapisane przepisy są do użytku własnego. Publikowanie
cudzych przepisów jako swoich to inna sprawa i wymagałoby zgody autorów.

## Rozwój

```bash
pytest                          # testy
rolki serve --reload            # autoreload przy zmianach
```

Struktura:

```
app/
  main.py                 # FastAPI: widoki HTML + REST
  jobs.py                 # kolejka w tle (ThreadPoolExecutor)
  cli.py                  # rolki add / list / serve
  schemas.py              # kształt przepisu = schemat dla modelu
  models.py, db.py        # SQLite przez SQLAlchemy
  cache.py                # cache adresowany treścią
  pipeline/
    downloader.py         # yt-dlp
    media.py              # ffmpeg: audio + kadry
    transcribe.py         # dostawcy transkrypcji (local / none)
    extractor.py          # zapytanie do Claude
    orchestrator.py       # spina wszystko razem
```

Miejsca przygotowane pod wersję komercyjną: `transcribe.py` ma warstwę dostawców
(dołożenie Whisper API to jedna klasa), a `jobs.py` można wymienić na Celery/RQ
bez ruszania pipeline'u.
