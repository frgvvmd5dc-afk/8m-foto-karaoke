# 8M Foto Karaoke — Windows und Mac

Ein lokales Programm für PowerPoint-Karaoke mit **gemischter Zufallsauswahl aus Fotos und Videos**. Die Stichwortkarten kommen von einer anderen Person. Medien werden weder hochgeladen noch verändert. Jedes gewählte Dateipfad-Medium kommt pro Abend höchstens einmal neu dran; Zurückblättern ist jederzeit möglich.

## Verwendung

1. **Quellen wählen:** Mehrere Ordner hinzufügen; Unterordner werden automatisch eingelesen. Ein Unterordner kann mit Doppelklick ausgeschlossen oder wieder einbezogen werden. USB-Sticks und Netzlaufwerke müssen erreichbar bleiben. Bei Änderungen „Quellen neu einlesen“ wählen.
2. **Bildschirm wählen:** Auf dem Beamer/zweiten Bildschirm erscheint die Bühne, auf dem anderen die Verwaltung. Mit „Karaoke starten“ öffnen; mit dem ersten Klick bzw. der Leertaste beginnt die Ziehung. Nach Neustart wird das zuletzt gezogene Medium wieder angezeigt.
3. **Vortragen:** Klick auf ein Foto, Leertaste oder → zeigt das nächste Medium. ← zeigt frühere Medien; beim Vorwärtsgehen wird der Verlauf zuerst durchlaufen. „Überspringen“ oder `S` zieht sofort ein neues Medium. Ein Video wird mit Ton gestartet und bleibt nach dem Ende stehen, bis weitergeschaltet wird. Über `P` oder die Schaltfläche pausieren/fortsetzen, mit dem Regler zur gewünschten Stelle springen und die Lautstärke einstellen.
4. **Ausschnitt:** Fotos sind zunächst ganz sichtbar. „Füllen“ oder `C` schaltet den Zuschnitt für das aktuelle Medium um. Bei einem Foto einen Ausschnitt mit der Maus aufziehen, um ihn zu vergrößern; „Ausschnitt zurück“ oder `R` setzt ihn zurück. Bei Videos ist das Verhältnis einpassen/füllen wählbar. `Esc` schließt die Bühne.
5. **Neuer Abend:** Eine bestätigte Rücksetzung gibt alle Medien erneut frei. Wenn alle Medien gezogen wurden, bietet das Programm Neustart mit denselben Quellen oder neue Quellen an.

### Diashow nach dem Karaoke

Im Hauptmenü „Diashow starten“ wählen. Fotos und Videos laufen dann automatisch in zufälliger Reihenfolge. Die Fotodauer lässt sich im Hauptmenü auf 5, 8, 12, 20 oder 30 Sekunden einstellen. **Videos starten automatisch mit Ton und werden ganz abgespielt; unmittelbar nach dem Ende folgt das nächste zufällige Medium.** Nach einer vollständigen Runde beginnt eine neu gemischte Reihenfolge. Ein Medium erscheint innerhalb einer Runde nur einmal, und sofern mindestens zwei Dateien vorhanden sind, kommt dieselbe Datei nicht direkt an der Rundengrenze erneut. `P` hält die Diashow an und setzt sie fort; „Nächstes“/Leertaste springt manuell weiter. `Esc` bringt dich ins Hauptmenü zurück. Die Diashow ändert den gespeicherten Karaoke-Ziehungsstand nicht.

Der Ziehungsstand liegt unter Windows in `%APPDATA%\8M Foto Karaoke\abend.json` und auf dem Mac unter `~/Library/Application Support/8M Foto Karaoke/abend.json`. Die Windows-Fassung übernimmt den Stand der früheren Nur-Foto-Version. Identische Kopien an unterschiedlichen Pfaden zählen separat.

**Fotoformate:** JPG/JPEG/JFIF, PNG, BMP/DIB, GIF (erstes Bild), TIFF, WebP, ICO, PCX, TGA und PPM/PGM/PBM. **Videodateien im Suchlauf:** MP4, M4V, MOV, AVI, MKV, WMV, MPG/MPEG, 3GP, WebM, MTS/M2TS, FLV und VOB. Die Endung allein garantiert die Abspielbarkeit nicht: der Videocodec, Audiocodec, Dateizustand und Betriebssystem-Build bestimmen sie mit. Wenn ein Video nicht dekodiert wird, erscheint eine Meldung und „Nächstes“ führt weiter. Gerade alte Kameradateien bitte vor der Veranstaltung mit einigen Stichproben prüfen. HEIC und RAW-Fotos sind nicht enthalten.

## Windows-Versionen bauen

Auf **Windows 10/11 x64** Python 3.12+ sowie für den Installer [Inno Setup 6](https://jrsoftware.org/isinfo.php) installieren. Im Projektordner `./build-windows.ps1` in PowerShell ausführen. Das Skript installiert die Abhängigkeiten lokal und erzeugt:

- `dist/8M-Foto-Karaoke.exe` — portable Windows-App.
- `dist/8M-Foto-Karaoke-Setup.exe` — Windows-Installer, wenn Inno Setup vorhanden ist.

## Mac-Versionen bauen

Auf einem **Mac mit macOS 15 oder neuer** Python 3.12+ installieren und im Terminal im Projektordner `bash build-mac.sh` ausführen. Das Skript erzeugt `dist/8M-Foto-Karaoke-macOS.dmg` mit einer `.app` zum Kopieren nach „Programme“. Für Intel und Apple Silicon getrennt auf dem jeweiligen Mac bauen.

Alternativ den **Inhalt** dieses Projektordners als Wurzel in ein GitHub-Repository hochladen und unter **Actions → Windows und Mac herunterladen → Run workflow** starten. Der Workflow erzeugt die Windows-Dateien sowie je ein Mac-DMG für Intel und Apple Silicon als getrennte Artefakte. Python ist auf den Zielrechnern nicht erforderlich. Das Bauen benötigt Internet, die fertige Anwendung nicht. Die Builds sind ohne eigene Codesignatur und Apple-Notarisierung; Windows SmartScreen bzw. macOS Gatekeeper können beim erstmaligen Start nachfragen. Zum reibungslosen öffentlichen Verteilen sollten die Pakete signiert bzw. notarisiert werden.

Das eigenständige 8M-Design orientiert sich an den Farbakzenten der [BORG-Website](https://www.borgwn.at/). Dies ist keine offizielle Veröffentlichung der Schule.

## Entwicklung und Prüfen

`python -m unittest discover -s tests` prüft Quellen, Ausschlüsse, gemischte Ziehung, Wiederaufnahme und Speichern. Die Videoanzeige, Tonwiedergabe, Monitorwahl und Installer benötigen zusätzlich praktische Tests auf Windows und Mac mit echten Foto- und Videodateien. In der Linux-Arbeitsumgebung wurden keine Windows- oder Mac-Installationspakete gebaut.
