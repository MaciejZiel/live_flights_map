**Pełna Lista**
Poniżej masz pełną listę rzeczy, które mam traktować jako backlog do doprowadzenia tej aplikacji jak najbliżej `FR24 1:1`. Niczego z wcześniejszych ustaleń tu nie pomijam.

**1. Rzeczy, które są teraz za duże / za głośne i trzeba je uprościć**
- Za dużo paneli i overlayów jednocześnie: topbar, ribbon, status strip, quick card, lewy panel, prawy panel, bottom dock.
- Za dużo funkcji konkuruje o uwagę naraz zamiast prowadzić użytkownika jednym głównym workflow.
- `Guide` jest za mocno eksponowany.
- `Workspace` jest za mocno eksponowany.
- `Notes` są za mocno eksponowane.
- `Comparison` jest za mocno eksponowany.
- `Monitoring sessions` są za mocno eksponowane.
- `Saved views` są za mocno eksponowane.
- Za dużo stanu i funkcji siedzi lokalnie w przeglądarce zamiast wyglądać jak produktowy system.
- UI wciąż bywa zbyt „nasze”, a za mało „FR24”.

**2. Rzeczy, których jest za mało albo brakuje**
- Search nie jest jeszcze pełnym centrum aplikacji.
- Search musi wyszukiwać: `flight`, `callsign`, `icao24`, `registration`, `aircraft type`, `airline`, `route`, `airport`, `location`.
- Search musi zwracać wyniki pogrupowane typami encji.
- Search musi mieć szybkie podpowiedzi i jasny workflow po wyborze wyniku.
- Brakuje pełnego workflow lotnisk.
- Brakuje pinów lotnisk.
- Brakuje panelu szczegółów lotniska.
- Brakuje `arrivals`.
- Brakuje `departures`.
- Brakuje widoku ruchu naziemnego / on-ground.
- Brakuje historii lotniska.
- Brakuje pogodowych danych lotniskowych.
- Brakuje warstw mapy bliższych FR24.
- Brakuje weather layers.
- Brakuje bardziej lotniczych warstw / chart-like overlays.
- Brakuje granic / operational overlays, jeśli mają sens dla tego produktu.
- Brakuje bardziej kompletnego systemu filtrów.
- Brakuje pełnych kategorii typu `Passenger`, `Cargo`, `Business`, `Military`, `Helicopter`, `Government`, `Glider`, `Light aircraft`.
- Brakuje lepszego trybu wygaszania samolotów spoza aktywnych filtrów.
- Brakuje pełniejszego systemu bookmarków.
- Brakuje bookmarków dla `aircraft`.
- Brakuje bookmarków dla `flights`.
- Brakuje bookmarków dla `airports`.
- Brakuje bookmarków dla `locations`.
- Brakuje kont użytkowników.
- Brakuje synchronizacji preferencji i bookmarków między sesjami.
- Brakuje pełniejszego systemu alertów.
- Brakuje historii lotów na poziomie produktu, nie tylko lokalnego archiwum.
- Brakuje bardziej kompletnego replay / playback.

**3. Rzeczy, które już są, ale nie działają jeszcze idealnie**
- Panel wybranego lotu nie jest jeszcze tak dominujący i czytelny jak w FR24.
- Search po wyborze wyniku nie prowadzi jeszcze użytkownika tak pewnie jak w FR24.
- Replay istnieje, ale jest jeszcze za płytki.
- Filtry istnieją, ale nie są jeszcze na poziomie FR24.
- Globalny board istnieje, ale musi być dalej dopieszczony wizualnie i workflowowo.
- Quick card istnieje, ale trzeba sprawdzić, czy nie jest za głośna wobec głównego inspectora.
- Mobile działa lepiej niż wcześniej, ale wciąż nie daje tak płynnego doświadczenia jak desktop.
- Cały shell aplikacji wymaga dalszego uproszczenia i hierarchizacji.
- Zaznaczenie samolotu i wejście w szczegóły jest już lepsze, ale nadal nie jest `1:1 FR24`.
- Ogólna charakterystyka wizualna nadal nie jest wystarczająco blisko FR24.

**4. Główne rzeczy do zrobienia w UI/UX**
- Uprościć cały shell aplikacji.
- Zostawić mapę jako absolutne centrum.
- Uczynić search głównym wejściem do interakcji.
- Uczynić wybór samolotu głównym workflow.
- Uczynić prawy inspector głównym miejscem pracy z danym lotem.
- Ograniczyć liczbę równorzędnych sekcji widocznych naraz.
- Zredukować wizualny szum.
- Poprawić hierarchię informacji.
- Poprawić spacing.
- Poprawić typography.
- Poprawić kontrast.
- Poprawić stany hover / selected / active / disabled.
- Ujednolicić język wizualny całej aplikacji.
- Dopracować animacje i przejścia tak, żeby były znaczące, a nie dekoracyjne.
- Dopracować mobile drawers i mobile navigation.
- Doprowadzić UI do stanu czytelnego, uporządkowanego i bez syfu.

**5. Search i workflow wyników**
- Przebudować search na model encji, a nie tylko prostych wyników lotów.
- Dodać wyniki dla lotów.
- Dodać wyniki dla samolotów.
- Dodać wyniki dla rejestracji.
- Dodać wyniki dla airline.
- Dodać wyniki dla airport.
- Dodać wyniki dla route.
- Dodać wyniki dla location.
- Pogrupować wyniki.
- Dodać czytelne ikony typów wyników.
- Dodać secondary metadata w wynikach.
- Dodać szybkie otwieranie wyników klawiaturą.
- Po kliknięciu wyniku lotu: fokus mapy + otwarcie inspectora + trail + details.
- Po kliknięciu wyniku lotniska: fokus mapy + airport panel.
- Po kliknięciu wyniku location: fokus mapy na obszar.
- Po kliknięciu wyniku samolotu: fokus + aircraft/flight panel.
- Dodać sensowny empty state.
- Dodać sensowny loading state.
- Dodać sensowną obsługę błędów search.

**6. Flight panel / aircraft inspector**
- Zrobić prawy panel bliższy FR24.
- Pokazać callsign jako główny nagłówek.
- Pokazać route jako kluczowy kontekst.
- Pokazać registration.
- Pokazać aircraft type.
- Pokazać airline / operator.
- Pokazać origin.
- Pokazać destination.
- Pokazać altitude.
- Pokazać speed.
- Pokazać heading.
- Pokazać squawk, jeśli dostępny.
- Pokazać vertical speed, jeśli dostępne.
- Pokazać source / confidence / freshness.
- Pokazać trail.
- Pokazać status lotu i jakość danych.
- Dodać szybkie akcje: `follow`, `bookmark`, `share`, `replay`, `alert`.
- Dodać czytelniejszy layout kart / sekcji.
- Ograniczyć elementy drugorzędne, które dziś rozpraszają.

**7. Airport workflow**
- Dodać encję lotniska do modelu aplikacji.
- Dodać piny lotnisk.
- Dodać możliwość kliknięcia lotniska na mapie.
- Dodać panel lotniska.
- Dodać tab `Arrivals`.
- Dodać tab `Departures`.
- Dodać podstawowe statystyki lotniska.
- Dodać pogodę dla lotniska, jeśli źródło danych pozwoli.
- Dodać powiązanie lotów z lotniskami.
- Dodać airport search results.
- Dodać airport bookmarks.
- Dodać airport share links.

**8. Replay / playback / historia**
- Rozbudować replay do poziomu bardziej zbliżonego do FR24.
- Dodać wybór czasu i zakresu.
- Dodać lepszy timeline feel.
- Dodać single-flight playback.
- Dodać global playback.
- Dodać wyraźne przełączanie `Live` / `Replay`.
- Dodać lepsze oznaczanie czasu danych.
- Dodać historyczne ślady lotu.
- Dodać historię konkretnego samolotu.
- Dodać historię konkretnego lotu.
- Dodać historię lotniska.
- Dodać lepszy backendowy zapis snapshotów, tracków i indeksów wyszukiwania.

**9. Filtry**
- Dodać pełniejszy zestaw filtrów typów lotów i statków powietrznych.
- Dodać filtry po airline.
- Dodać filtry po aircraft type.
- Dodać filtry po altitude.
- Dodać filtry po speed.
- Dodać filtry po statusie.
- Dodać filtry po regionie.
- Dodać lepsze aktywne tokeny filtrów.
- Dodać tryb przygaszania samolotów niespełniających filtrów zamiast brutalnego ukrywania, jeśli to poprawia UX.
- Dodać presety filtrów bliższe FR24.

**10. Most tracked / globalny board**
- `Most tracked flights` ma być zawsze globalne, niezależne od aktualnego bbox i widoku mapy.
- Musi być stale widoczne.
- Musi dawać wejście w lot z dowolnego miejsca świata.
- Kliknięcie w lot z boardu ma fokusować mapę na ten lot i otwierać szczegóły.
- Ranking musi być wiarygodny i odświeżany sensownie.
- Trzeba go dalej dopracować wizualnie.

**11. Map interaction**
- Dalej dopracować markery.
- Dalej dopracować selected state.
- Dalej dopracować hover.
- Dalej dopracować tooltipy.
- Dalej dopracować klastry.
- Dalej dopracować zachowanie po kliknięciu samolotu.
- Dalej dopracować zachowanie po kliknięciu pustej mapy.
- Dalej dopracować focus mapy na wybrany lot.
- Dodać bardziej FR24-like feeling map controls.
- Dodać warstwy mapy bliższe FR24.
- Dodać przełączanie map tak, żeby nie wywoływało wrażenia „pustego ekranu”.

**12. Bookmarks / watchlist / konta**
- Rozbudować bookmarki.
- Rozbudować watchlist.
- Połączyć je z kontami użytkowników.
- Dodać zapis do backendu.
- Dodać synchronizację między sesjami.
- Dodać czytelny workflow zarządzania obserwowanymi lotami.
- Dodać obsługę lotów, samolotów, lotnisk i lokalizacji.

**13. Alerts / monitoring**
- Dodać alerty na konkretny lot.
- Dodać alerty na konkretny samolot.
- Dodać alerty na lotnisko.
- Dodać alerty na wejście w obszar.
- Dodać alerty na start / lądowanie.
- Dodać alerty na altitude / speed / route, jeśli to ma sens i jest wspierane danymi.
- Przenieść alerty z poziomu „lokalnej funkcji” na poziom prawdziwego workflow produktowego.

**14. Backend / dane / jakość**
- Uporządkować pipeline danych.
- Rozdzielić `collector`, `normalizer`, `archive`, `api`, `alerts worker`, jeśli repo pójdzie dalej.
- Poprawić globalny cooldown providerów.
- Poprawić politykę cache.
- Poprawić trwały archive lotów.
- Poprawić indeksowanie danych pod search.
- Rozszerzyć model danych dla airport, airline, route, aircraft profile.
- Rozszerzyć szczegóły lotu.
- Poprawić odporność na błędy providerów.
- Poprawić jakość fallbacków.
- Dodać lepsze healthchecki i diagnostykę.
- Dodać lepsze logowanie błędów.
- Dodać lepszą obsługę rate limitów.
- Dodać lepsze źródła danych, jeśli będziemy chcieli naprawdę zbliżyć się jakością do FR24.

**15. Ograniczenie, którego nie wolno ignorować**
- UI i workflow da się zrobić bardzo blisko FR24.
- Jakości danych `1:1` nie da się uczciwie obiecać na samych publicznych feedach.
- Żeby dojść do poziomu danych FR24, potrzebne są lepsze feedy, historia, enrichment i mocniejsza infrastruktura.

**16. Kolejność, którą mam teraz trzymać**
1. Uproszczenie shella i schowanie nie-core rzeczy.
2. Przebudowa `search + result workflow` na model FR24.
3. Dopracowanie prawego `flight inspector`.
4. Dodanie pełnego `airport workflow`.
5. Rozbudowa `replay / playback / history`.
6. Rozbudowa filtrów i warstw mapy.
7. Rozbudowa bookmarków, watchlist i alertów.
8. Dopiero potem dalsze doszlifowanie funkcji pobocznych.

Jeśli chcesz, następną odpowiedzią mogę Ci to przepisać jeszcze w formie bardzo twardego backlogu `TODO`, punkt po punkcie do odhaczania, bez żadnego opisu.
