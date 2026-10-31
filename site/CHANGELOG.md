# GoonClient

Ein modularer Minecraft-Client als **Fabric-Mod** für **Minecraft 1.21.11** (Java 21, offizielle Mojang-Mappings).

| Komponente | Version |
|---|---|
| Minecraft | 1.21.11 |
| Fabric Loader | 0.19.3 |
| Fabric API | 0.141.5+1.21.11 |
| Fabric Loom | 1.17-SNAPSHOT (`net.fabricmc.fabric-loom-remap`) |
| Gradle | 9.5.0 |
| Java | 21 |

## 1. Projekt in IntelliJ IDEA öffnen

1. Java 21 installieren (z. B. Temurin 21) und in IntelliJ unter *File > Project Structure > SDK* auswählen.
2. *File > Open* und den Ordner `GoonClient` wählen (die Datei `build.gradle` auswählen, falls gefragt: "Open as Project").
3. **Gradle Wrapper erzeugen** (einmalig, im Terminal von IntelliJ im Projektordner):
   ```
   gradle wrapper --gradle-version 9.5.0
   ```
   Hast du kein Gradle installiert, kopiere stattdessen `gradlew`, `gradlew.bat` und den Ordner `gradle/wrapper/` aus einem frischen Projekt von https://fabricmc.net/develop/template in diesen Ordner und setze in `gradle/wrapper/gradle-wrapper.properties` die `distributionUrl` auf Gradle 9.5.0.
4. In IntelliJ den Gradle-Refresh-Button drücken und warten, bis Minecraft heruntergeladen und verarbeitet ist (beim ersten Mal einige Minuten).

## 2. Starten und bauen

| Aktion | Windows | macOS / Linux |
|---|---|---|
| Minecraft mit Mod starten | `gradlew.bat runClient` | `./gradlew runClient` |
| JAR bauen | `gradlew.bat build` | `./gradlew build` |

Die fertige Datei liegt danach in `build/libs/goonclient-3.15.0.jar`
(**nicht** die Datei mit `-sources`).

## 3. JAR installieren

1. Fabric Loader für 1.21.11 über den Fabric-Installer installieren.
2. `fabric-api-0.141.5+1.21.11.jar` und `goonclient-3.15.0.jar` in den Ordner `.minecraft/mods` kopieren.
3. Minecraft mit dem Fabric-Profil starten, eine Welt betreten und **Right Shift** drücken.

## 4. Projektstruktur

```
src/main/java/com/goonclient/
    GoonClientMod.java            gemeinsamer Einstieg, Konstanten (MOD_ID, Logger)
src/client/java/com/goonclient/
    GoonClientClient.java         Client-Einstieg: registriert alles, lädt Config, Ticks
    config/      ConfigManager (JSON laden/speichern), ConfigSection
    settings/    Setting + Boolean/Number/Slider/Mode/Color/Keybind/String/Button, Feature, ClientSettings
    module/      Module, HudModule, ModuleManager, ModuleCategory (Combat, Movement, Render, HUD, Utility, Misc)
    module/impl/ BuiltInModules (hier neue Module eintragen), SaturationModule, MotionBlurModule, HUD-Module ...
    render/      PostEffects (steuert Saturation + Motion Blur als Post-Processing)
    gadgets/     Gadget, GadgetManager, SessionTimerGadget, CalculatorGadget
    cosmetics/   Theme, Cosmetic, CosmeticsManager (10 Themes, Effekte: Glow, Pulse, Particles, Rainbow)
    keybind/     KeybindManager (Menütaste + Modul-Tasten)
    hud/         HudManager (zeichnet HUD-Module und den Post-Effect-Pass)
    gui/         ClientScreen, Sidebar, UiContext, Icon
    gui/pages/   Page, ModuleTab (Karten-Raster + Seitenpanel), HomePage, CosmeticsPage, SettingsPage,
                 AboutPage + AboutTexts (hier die 100 Sätze ändern)
    gui/widget/  ModuleCard, SettingsPanel, SearchBar, ScrollPane, SettingRenderer, CardList
    gui/widget/settings/  ein Widget pro Einstellungstyp (Boolean, Slider, Number, Mode, Color, Keybind, Text, Button)
    util/        Animation, ColorUtil, TextWrap, RenderUtil, KeyUtil, ClientInfo, ExpressionParser (Rechner)
src/main/java/com/goonclient/network/   CosmeticsPayload + CosmeticsRelay (Protokoll und Server-Weiterleitung, läuft auf Client UND Server)
src/client/resources/assets/goonclient/
    textures/cape/  5 Cape-Texturen (erzeugt mit tools/generate_capes.py)
    shaders/post/   saturation.fsh, blur_blend.fsh, copy.fsh
    post_effect/    302 vorgefertigte Effekt-Varianten (Sättigung, Blur, Helligkeit/Kontrast) (erzeugt mit tools/generate_post_effects.py)
tools/generate_post_effects.py   erzeugt die post_effect-JSONs neu (z. B. andere Blur-Stufen)
```

Konfiguration: `.minecraft/config/goonclient/config.json` (alte Konfigurationen funktionieren weiter).

## 5. Eigenes Modul hinzufügen

1. Neue Klasse in `module/impl/`, z. B. `ZoomInfoModule extends HudModule` (oder `extends Module` mit einer `ModuleCategory`).
2. Einstellungen im Konstruktor mit `addSetting(new BooleanSetting(...))` usw. anlegen.
3. Eine Zeile in `BuiltInModules.registerAll` ergänzen: `manager.register(new ZoomInfoModule());`

Das Modul erscheint automatisch als Karte in seinem Kategorie-Tab, ist über die Suche auffindbar und wird gespeichert.
Neue Einstellungstypen: ein Widget in `gui/widget/settings/` und eine Zeile in `SettingWidgets.of(...)`.
Neuer Tab: eine Zeile in `ClientScreen.buildTabs()`.

## 6. Bekannte Prüfstellen beim ersten Build

Der Code wurde ohne Zugriff auf Fabric/Mojang geschrieben und **noch nicht kompiliert**.
Sollte der Build fehlschlagen, sind das die wahrscheinlichsten Stellen (Fehlermeldung kopieren und weitergeben):

- `cosmetics/CapeDesigns.java`: `ClientAsset.ResourceTexture(Identifier, Identifier)` und `net.minecraft.core.ClientAsset`
- `cosmetics/NetworkCosmetics.java`: Konstruktor `PlayerSkin(body, cape, elytra, model, secure)`, `Style#withInsertion/getInsertion`
- `mixin/AbstractClientPlayerMixin.java`, `EntityNameMixin.java`, `PlayerNameMixin.java`: Methoden `getSkin` und `getDisplayName`
- `network/*`: Fabric-Networking (`PayloadTypeRegistry`, `ServerPlayNetworking`, `ClientPlayNetworking.canSend`, `ClientPlayConnectionEvents`)
- `render/PostEffects.java`: `PostChain`, `ShaderManager#getPostChain`, `GraphicsResourceAllocator.UNPOOLED`
- `hud/HudManager.java`: `HudElementRegistry.addFirst/addLast/replaceElement`, `Identifier.fromNamespaceAndPath`
- Shader-Dateien und `post_effect/*.json`: Format der 1.21.11-Post-Effekte (beim Start steht ein Fehler im Log, das Modul zeigt dann "Shader error")
- `gui/ClientScreen.java`: `KeyEvent`, `MouseButtonEvent`, `CharacterEvent`, `g.fillGradient`
- `gui/UiContext.java`: `g.pose().pushMatrix()/translate/scale/popMatrix()`, `g.enableScissor/disableScissor`
- `util/KeyUtil.java`: `InputConstants.Type.KEYSYM.getOrCreate(int).getDisplayName()`
- `build.gradle`: Loom-Plugin-ID/-Version (siehe https://fabricmc.net/develop)

## 7. Render-Module und FPS

- **Color Saturation** (Render): ca. 2 Vollbild-Durchgänge. Kaum messbar.
- **Motion Blur** (Render): Frame-Blending, 3 Durchgänge plus ein zusätzlicher Bildpuffer. Etwas teurer.
- **Beide zusammen**: ein gemeinsamer Effekt mit 3 Durchgängen, also keine doppelten Passes.
- Die Stärke des Blurs hängt von der FPS ab (Blending pro Bild). Bei F1 (HUD aus) pausiert der Effekt.

## 8. Taschenrechner (Gadgets)

Gadgets-Tab, Karte "Calculator", dort Knopf **Open** (geht auch bei ausgeschaltetem Gadget). Ist das Gadget eingeschaltet,
kann man zusätzlich eine Taste "Open key" belegen. Tastatur im Rechner: Ziffern, `+ - * / ( ) %`, `,` oder `.`, Enter = berechnen,
Backspace = letztes Zeichen, Entf = alles löschen, ESC = schließen. Geschlossen greift der Rechner nicht in die Steuerung ein.
Parser-Test (ohne Minecraft):

```
javac -d out src/client/java/com/goonclient/util/ExpressionParser.java tools/ExpressionParserTest.java
java -cp out ExpressionParserTest
```

## 9. Goon Cosmetics (Capes, Badges, animierte Namensschilder)

Menü-Tab **Goon Cosmetics**. Oben steht immer die Live-Vorschau (Cape, Name, Badge, Namensschild). Darunter die Bereiche
**Capes**, **Badges**, **Animated Nametags**, **Effects & Themes** und **Settings**.

- **Capes**: Design anklicken (Vorschau), dann "Equip". "Remove cape" nimmt sie ab. Cape und Badge sind jetzt **standardmäßig an**
  (vorher waren sie aus und in einer eingeklappten Karte versteckt, das war der Hauptgrund für "unsichtbar").
- **Badges**: Stil wählen (Star, Diamond, Heart, Tag, Crown, Bolt oder **Custom** mit eigenem Text bis 8 Zeichen), Farbe, Position (vor/nach dem Namen).
- **Animated Nametags**: Rainbow, Gradient, Pulse, Wave, Glow, RGB, Static; zwei Farben, Geschwindigkeit, "Animate" (aus = Standbild), Fett.
- **Settings**: was du von anderen sehen willst (Capes/Badges/Namensschilder getrennt), Namensschild über dem Kopf / im Chat, eigenes Namensschild
  in der Third-Person-Ansicht, Reichweite. Darunter eine Diagnose, die zeigt, ob die Mixin-Eingriffe in deiner Minecraft-Version laufen.

**Wer sieht was (wichtig):** Du siehst alles immer an dir selbst, auch ohne Server-Unterstützung. Andere GoonClient-Spieler sehen es nur, wenn
**auf dem Server GoonClient installiert ist** (der Server leitet die Daten weiter; Kanal `goonclient:cosmetics`, Protokoll 2) oder im
Einzelspieler mit "Für LAN öffnen". Auf reinen Vanilla-Servern ist das technisch nicht möglich. Spieler ohne GoonClient bekommen nie Pakete.
Der Client sendet Änderungen sofort (höchstens alle 0,6 s) und zur Sicherheit alle 60 s erneut.

Grenzen: Das Namensschild ist ein Text mit einer Farbe pro Buchstabe. Deshalb gibt es **keine** frei einstellbare Transparenz, Größe und Höhe
(das ginge nur mit einem eigenen Nametag-Renderer). Im Chat ist das Namensschild ein Standbild. Der Chat-Absender wird anhand des Namens am Anfang der
Nachricht erkannt (Minecraft liefert dem Client den Absender dort nicht als eigenes Feld), und nur für Spieler, deren Name der Client schon kennt
(in Reichweite gesehen).

## 10. Sounds

Acht selbst synthetisierte, lizenzfreie Sounds (`tools/generate_sounds.py`, Ergebnis in `assets/goonclient/sounds/ui/*.ogg`): Menü öffnen, schließen,
Modul an, Modul aus, Knopf, gespeichert ("Save now"), Profil-/Theme-Wechsel, Fehler. Der Öffnen-Sound läuft genau dort, wo die Menütaste das Menü öffnet,
also einmal pro Öffnen (nicht bei Fenstergrößen-Änderung). Einstellungen: Settings-Tab, Abschnitt **Sound Settings** (Gesamt an/aus, GUI-Sounds,
Modul-Sounds, getrennte Lautstärke 0-100 %, reduzierter Modus, Vorschau-Knöpfe). Alles wird in der `config.json` gespeichert (Abschnitt `sounds`).
Es gibt kein Profil-System im Client; der Profil-Sound läuft beim Wechsel von Theme oder Cape.

## 11. Tests ohne Minecraft

```
javac -d build/tools src/client/java/com/goonclient/util/ColorUtil.java src/client/java/com/goonclient/cosmetics/NametagColors.java src/client/java/com/goonclient/cosmetics/NameMatcher.java src/main/java/com/goonclient/network/CosmeticsRules.java tools/CosmeticsLogicTest.java
java -cp build/tools CosmeticsLogicTest
```

## 12. Waypoints

Tab **Waypoints** (Menü) und Modul **Waypoints** (Kategorie Utility, standardmäßig an).

- **Erstellen**: "Add at my position" (mit Name, Farbe, Icon aus dem Formular), manuell über X/Y/Z ("Add with coordinates", leere Felder = deine Position)
  oder mit der Taste "Quick waypoint key" (Modul-Einstellung, standardmäßig nicht belegt).
- **Verwalten**: Suche, Filter (All / Enabled / Disabled / This dimension), pro Waypoint **On/Off**, **Track**, **Edit** (Name, Koordinaten, Farbe, Icon), **Delete** (zweiter Klick bestätigt).
- **Anzeige** (nach dem Spawn-Beispielbild): Label mit farbigem Rahmen und Entfernung ("Spawn [7m]"), Lichtstrahl, Ring auf dem Boden, Funken.
  Der verfolgte Waypoint zeigt oben einen Pfeil mit Name, Entfernung und Koordinaten.
- **Speicherung**: in der `config.json` (Abschnitt `waypoints`), getrennt nach Einzelspieler-Welt (`world:<Name>`) und Server (`server:<Adresse>`), mit Dimension je Waypoint.
  Marker erscheinen nur in der Dimension, in der der Waypoint angelegt wurde.
- **Genauigkeit**: Die Marker werden aus Augenposition, Blickrichtung und dem eingestellten Sichtfeld selbst auf den Bildschirm gerechnet. Bei
  Sprint-/Effekt-Sichtfeld und in der Third-Person-Ansicht kann ein Marker leicht abweichen.

## 13. Durability Viewer

Modul **Durability Viewer** (Utility, standardmäßig an). Beim Hover über ein Item mit Haltbarkeit steht im Tooltip
`Durability: 496/500 (99%)` plus eine kleine Leiste. Zahlen, Prozent, Farben und Leiste sind einzeln abschaltbar; die Farbgrenzen (gelb/rot) sind einstellbar.
Mit F3+H ersetzt die Zeile die Vanilla-Zeile. Items ohne Haltbarkeit bekommen nichts.

## 14. Free Look

Modul **Free Look** (Movement). Taste unter "Keybind" im Modul belegen. **Mode**: Toggle (einmal drücken = an, nochmal = aus) oder Hold (nur solange gedrückt).
Einstellungen: Sensitivity, Smooth camera, Auto return (sanfte Rückkehr), Third person (schaltet beim Start in die Third-Person-Ansicht und danach zurück), Show message ("FreeLook Mode: Toggle").
Die echte Blick- und Bewegungsrichtung bleibt unverändert (Mausbewegung wird umgeleitet, es wird nichts anderes an den Server geschickt).
Ein gespeichertes "an" startet Free Look nie automatisch beim nächsten Spielstart.

## 15. Tests ohne Minecraft (Waypoints und Durability)

```
javac -d build/tools src/client/java/com/goonclient/waypoint/WaypointMath.java src/client/java/com/goonclient/util/DurabilityFormat.java tools/FeatureLogicTest.java
java -cp build/tools FeatureLogicTest
```

## Online-Sync (v3.4.0): Capes, Badges und Nametags auf jedem Server

Damit GoonClient-Spieler sich gegenseitig sehen, auch auf Servern ohne GoonClient (z. B. DuelPrac.net), nutzt der Client ein **Backend**, das du selbst betreiben musst. Ohne Backend funktioniert nur der alte Server-Relay (GoonClient auf dem Server) bzw. Singleplayer/LAN.

### Backend starten
Benötigt nur Python 3 (keine Pakete):

```
python3 tools/backend/server.py --host 127.0.0.1 --port 8080 --db cosmetics.sqlite3 --trust-proxy
```

- Stelle einen HTTPS-Reverse-Proxy davor (Caddy, nginx oder Cloudflare Tunnel) und gib dem Client die https-Adresse.
- Die Option `--insecure` ist nur für lokale Tests. Nie im Betrieb verwenden.
- Anmeldung: Der Client meldet sich über Mojang (`session/join`) an, das Backend prüft per `hasJoined`. Dein Minecraft-Token geht nur an Mojang, nie ans Backend.

### Im Spiel
Menü → Goon Cosmetics → Settings → *Online sync*: **Backend address** eintragen (z. B. `https://cosmetics.deinedomain.de`). Darunter siehst du den Status und kannst mit *Reconnect* neu verbinden.

### Tests
`bash tools/backend/run_test.sh <pfad/zu/gson.jar>` startet ein Mock-Mojang und das Backend und prüft Anmeldung, Upload, Abruf, Isolation zwischen Spielern und Fehlerfälle.

### Eine Adresse für alle Nutzer (wichtig)
Trage deine Backend-Adresse **einmal** in `src/client/java/com/goonclient/backend/BackendConfig.java` bei `DEFAULT_URL` ein und baue den Client neu. Wer diese Version nutzt, ist automatisch verbunden. Das Feld "Custom backend address" im Menü bleibt leer und ist nur für Sonderfälle.

Kostenlos hosten (Beispiele): ein kleiner Server (z. B. Render, Fly.io, ein Raspberry Pi) mit dem Startbefehl oben, davor HTTPS. Der Dienst muss dauerhaft erreichbar sein; die SQLite-Datei braucht einen persistenten Speicher.

## Update 3.5.0: Animierte Namen im Chat und Friendlist

### Chat-Namen
Namen von GoonClient-Spielern im Chat nutzen jetzt genau dieselbe Animation wie das Namensschild über dem Kopf
(`NametagStyles.colorAt`: gleiche Farben, Übergänge, Geschwindigkeit, Fettdruck). Der Chattext wird dabei nicht verändert:
die Farben der Namenszeichen werden beim Zeichnen jeder Zeile neu berechnet (Mixin `GuiMessageLineMixin`, Klasse
`ChatAnimation`). Zeilenumbrüche und Chat-Skalierung bleiben unberührt, Badges bleiben davor/dahinter stehen.
Erkannt wird ein Name an seinem Einfügetext (wie im Standard-Chat, der beim Shift-Klick den Namen einfügt).
Wenn der Eingriff zu deiner Minecraft-Version nicht passt, wird er übersprungen und der Name bleibt als Standbild.

### Friendlist
- Menü-Tab **Friends**: Name eingeben und "Add friend", oder einen Spieler aus "Nearby players" anklicken. Suche, Kopf,
  Online-Punkt, "Remove" mit Bestätigung ("Sure?"), kurze Ein- und Ausblend-Animation, Hinweis bei leerer Liste.
- Befehle: `/friend add <Name>`, `/friend remove <Name>`, `/friend list` (auch `/friends`), mit Namensvorschlägen.
- **Rechtsklick** auf einen Spielernamen im Chat fügt ihn hinzu.
- Modul **Friends** (Kategorie Utility): Hervorhebung mit Stern und Freundesfarbe über dem Kopf, in der Tab-Liste und im Chat
  (jeweils einzeln abschaltbar). Animierte Namensschilder behalten ihre Farben, der Stern kommt davor.
- Speicherung: UUID als Schlüssel (Name nur zur Anzeige, wird bei Umbenennung automatisch aktualisiert), in der `config.json`
  (Abschnitt `friends`). Keine Duplikate, höchstens 500 Freunde.
- Name zu UUID ohne unnötige Abfragen: Spieler in der Nähe, dann der Zwischenspeicher, erst dann Mojang (Hintergrund-Thread).
  Findet Mojang den Namen nicht, aber der Spieler ist auf dem Server online, gilt er als Offline-Modus-Spieler (UUID vom Server).

### Tests
`java -cp ... FriendLogicTest` (siehe Kopf von `tools/FriendLogicTest.java`): Namen, UUIDs, Duplikate, Speichern/Laden,
Mojang-Abfrage gegen einen lokalen Testserver, Chat-Namenserkennung.

## Update 3.6.0: Goon Coins, Goon Shop, Inventar und Emotes

**Goon Coins.** Pro Minute aktiven Spielens gibt es 1 Coin. Gezählt wird nur, wenn du in einer Welt bist, das Spiel nicht pausiert ist und das Fenster den Fokus hat. Nach 3 Minuten ohne Eingabe (Tasten, Maus, Blick) gilt man als AFK und es läuft nichts weiter; gedrückt gehaltene Tasten zählen nicht als Eingabe. Der Fortschritt zur nächsten Coin wird mitgespeichert, Neustarts bringen also weder Verlust noch Extra-Coins. Gespeichert wird in `config/goonclient/wallet.json` (atomar, mit Backup `wallet.json.bak` und Signatur; beschädigte Dateien werden erkannt und aus dem Backup geholt). Autosave alle 30 s, sofort bei jeder Coin und Käufen, beim Beenden und beim Verlassen einer Welt.
Anzeige: Münze + Guthaben in der Titelzeile des Menüs (mit Zählanimation, Puls und "+1"), Banner "+1 Goon Coin" im Spiel, das HUD-Modul "Goon Coins" (Guthaben, optional Zeit bis zur nächsten Coin), Statistik im Shop (verdient, ausgegeben, Spielzeit).

**Goon Shop** (Tab "Goon Shop"): Kategorien Emotes, Badges, Capes, Nametags, Filter nach Seltenheit, "Gekauftes ausblenden", Live-Vorschau (animierte Capes, Badge-Effekte, Nametag-Animationen, Emote-Figur), Preis, Guthaben nach dem Kauf, Kaufen mit Bestätigung, Konfetti/Flash beim Kauf, Ring beim Ausrüsten. Doppelkäufe und negatives Guthaben sind ausgeschlossen.
Preise (Coins = Minuten): Common 20-60, Uncommon 80-160, Rare 200-400, Epic 500-1000, Legendary 1500-3000. Das billigste Item ist nach etwa 20 Minuten Spielzeit da, ein Legendary nach gut 25 bis 50 Stunden.

**Inventar** (Tab "Inventory"): alles, was dir gehört (auch die Starter-Items), nach Kategorie und Seltenheit/Name sortiert; ausrüsten, ablegen, wechseln. Bei Emotes stellst du die 8 Plätze des Emote-Rads ein. In "Goon Cosmetics" sind nicht gekaufte Items als "Locked" markiert und lassen sich nicht ausrüsten; nicht gekaufte Items werden auch nicht an andere gesendet.

**Emotes:** Wave, Dance, Laugh, Heart, Cry, Flex, Dab, Salute, Spin, Celebrate. Rad: Taste B halten (einstellbar im Modul "Emotes"), Feld wählen, loslassen. Außerdem Schnelltaste und `/emote <name>`. Laufende Emotes werden beim Gehen beendet (abschaltbar). Andere GoonClient-Spieler sehen sie über das Backend (neuer Endpunkt `POST /v1/emote`, `GET /v1/emotes`).
**Wichtig:** `tools/backend/server.py` muss auf Render neu eingespielt werden (in GitHub ersetzen, Render deployt neu), sonst gibt es keine Emote-Synchronisierung; Coins, Shop und eigene Emotes gehen auch ohne.

**Neue Capes** werden aus `tools/GenerateCapes.java` erzeugt (`java tools/GenerateCapes.java`, schreibt PNGs nach `src/client/resources/assets/goonclient/textures/cape/`).

**Ehrliche Grenzen:**
- Coins liegen lokal. Die Signatur schützt nur gegen versehentliches Bearbeiten; wer den Code liest, kann sie fälschen. Es gibt keinen Server, der Käufe prüft.
- Zwei gleichzeitig laufende Clients desselben Kontos verdienen getrennt.
- Fremde Spieler können nicht auf Besitz geprüft werden (jeder GoonClient prüft nur sich selbst).
- Die Emote-Mixins (`HumanoidModelMixin`, `LivingEntityRendererMixin`, `LivingEntityRenderStateMixin`) sind für 1.21.11 geschrieben, aber nicht im Spiel getestet. Greifen sie nicht, bleibt Minecraft normal, Emotes erscheinen dann nur in der Vorschau; das Inventar zeigt dazu die Zeile "Animation hook". Stimmt eine Armrichtung nicht, ist das Vorzeichen in `HumanoidModelMixin` zu drehen.
- Eigene Arme in der Ego-Perspektive werden nicht animiert.

**Tests:** `ShopLogicTest` (Coins, AFK, Speicherung, Käufe, Rad, Emotes, Capes, Nametags, Badges, Presets), `bash tools/backend/run_test.sh <gson.jar>` (inkl. Emotes).

## Update 3.7.0: Hüte, Flügel und Accessoires (3D)

**Neu im Goon Shop:** drei Kategorien **Hats**, **Wings** und **Accessories** mit echten 3D-Modellen am Spieler (Kopf bzw. Rücken).
Je ein Hut, ein Paar Flügel und ein Accessoire können gleichzeitig getragen werden. Kaufen im Goon Shop, ausrüsten/ablegen im Shop oder im Inventar.

Preise nach Optik und Aufwand (schlicht = billig, leuchtend/animiert = teuer):

| Seltenheit | Hüte | Flügel | Accessoires |
|---|---|---|---|
| Common | Baseball Cap 30, Beanie 45 | Paper Wings 50 | Sunglasses 35, Headphones 55 |
| Uncommon | Chef Hat 85, Top Hat 120, Cowboy Hat 150 | Bat Wings 150 | Cat Ears 90, Cozy Scarf 110, Backpack 140 |
| Rare | Wizard Hat 260, Golden Crown 340, Viking Helmet 380 | Fairy Wings 300, Angel Wings 390 | Devil Horns 240 |
| Epic | Flame Crown 800 | Demon Wings 700, Dragon Wings 950 | Neon Visor 600, Halo 750 |
| Legendary | Cosmic Top Hat 2000 | Phoenix Wings 2200, Prism Wings 2800 | Orbiting Crystals 1800 |

Flügel schlagen, Halo/Kristalle/Sterne kreisen, leuchtende Teile haben volle Helligkeit (auch nachts), Regenbogen-Teile wechseln die Farbe.
Die Vorschau im Shop zeigt dieselben Quader wie im Spiel (Flügel und Rucksack von hinten).

**Wer sieht es:** Du siehst deine Accessoires immer selbst (Third Person, F5). Andere Spieler mit GoonClient **3.7.0** sehen sie
über das Backend auf jedem Server (wie Capes/Badges), sofern dort `tools/backend/server.py` in der neuen Version läuft
(**wichtig:** `server.py` auf Render neu einspielen, sonst verwirft das alte Backend die neuen Felder `hat`, `wings`, `accessory`).
Auf Servern mit GoonClient-Relay läuft es über den neuen Kanal `goonclient:cosmetics_v3` (Protokoll 3); alte Clients bekommen nie Pakete mit unbekannten Feldern.
Einstellung "Show other players' accessories" (Goon Cosmetics → Settings) blendet fremde Accessoires aus.

**Technik:** Designs in `cosmetics/AccessoryDesigns.java` (reine Daten, eine Zeile pro Quader), gezeichnet von `cosmetics/AccessoryLayer.java`
(Render-Ebene am Spielermodell, registriert über Fabrics `LivingEntityFeatureRendererRegistrationCallback`). Neues Design: Methode in
`AccessoryDesigns` ergänzen und eine Zeile im `ShopCatalog`. `ShopLogicTest` prüft, dass Katalog und Designs zusammenpassen.

## Update 3.8.0: Codes für Goon Coins

Im **Goon Shop** gibt es unter dem Guthaben ein Feld **Redeem code**, alternativ im Chat `/redeem <code>`.
Groß-/Kleinschreibung, Leerzeichen und Bindestriche spielen keine Rolle.

**Jeder Code gilt pro Spieler nur einmal:**
- Lokal: Die Id jedes eingelösten Codes steht signiert in `wallet.json`. Ein zweiter Versuch wird abgelehnt.
- Online (Backend angemeldet): Das Backend speichert pro Minecraft-UUID, welche Codes eingelöst wurden (Tabelle `redeemed`,
  Endpunkt `POST /v1/redeem`). Damit hilft auch Neuinstallieren oder Löschen der `wallet.json` nicht.
  **`tools/backend/server.py` muss dafür auf Render neu eingespielt werden.** Mit der alten server.py (HTTP 404) oder ohne
  Online-Login wird nur lokal geprüft.

**Neuen Code anlegen:** `java tools/MakeRedeemCode.java` (zufällig) oder `java tools/MakeRedeemCode.java GOON-MEIN-CODE`,
die ausgegebene Zeile mit neuer Id und Coin-Anzahl in `shop/RedeemCodes.java` bei `ALL` eintragen und den Client neu bauen.
Im Programm steht nur der Hash, nicht der Code selbst. Ids nie wiederverwenden.

## Update 3.9.0: Custom Hitboxes, Freundschaftsanfragen, Freundes-Stats

### Custom Hitboxes (Modul, Kategorie Render)
Zeigt die echten Treffer-Boxen von Entities, frei gestaltbar: getrennt an/aus für Spieler, Monster, Tiere, Items und die eigene Hitbox (Third Person);
Stil **Outline**, **Filled** oder **Outline + Fill**; Farbe, eigene Monster-Farbe, Freunde in der Freundesfarbe, eigene Farbe für das anvisierte Ziel;
Linienstärke, Füll-Deckkraft, optisches Vergrößern, Augenhöhe-Linie, Blickrichtung, Reichweite. Rein optisch, ändert nichts an der Spielmechanik.
Technik: `DebugRendererMixin` hängt sich an Minecrafts Gizmo-System (dort, wo auch F3+B zeichnet).

### Freundschaftsanfragen
- Wer jemanden hinzufügt (Feld, `/friend add`, Rechtsklick im Chat), schickt ihm automatisch eine **Freundschaftsanfrage** über das Backend.
- Der andere bekommt eine Chat-Meldung und sieht oben im Friends-Tab **Friend requests** mit **Accept** / **Decline**; alternativ `/friend accept <name>`,
  `/friend decline <name>`, `/friend requests`. Haben beide sich gegenseitig angefragt, sind sie sofort Freunde.
- In der Liste steht hinter dem Namen **Confirmed** oder **Request sent**; ältere, nur lokal eingetragene Freunde haben einen Knopf **Send request**.
- Entfernen beendet die Freundschaft auch beim Backend. Die lokale Liste (Hervorheben) funktioniert weiter ohne Backend.

### Stats von Freunden
Knopf **Stats** bei einem Freund: Goon Coins, insgesamt verdient, Spielzeit, Anzahl gekaufter Items, was er gerade trägt (Cape mit Bild, Badge, Nametag,
Hut, Flügel, Accessoire) und alle gekauften Capes, Badges, Nametags, 3D-Items und Emotes. Jeder Client lädt seine Stats höchstens einmal pro Minute hoch.
**Das Backend gibt Stats nur an bestätigte Freunde heraus** (sonst HTTP 403).

### Backend (wichtig)
**`tools/backend/server.py` auf Render neu einspielen.** Neue Tabellen `names`, `friend_requests`, `friendships`, `stats`; neue Endpunkte siehe Kopf von server.py.
Ohne neue server.py zeigt der Friends-Tab "The backend does not support friend requests yet". Funktioniert nur mit echten Minecraft-Konten (Online-Login).

### Tests
`py -3 tools/backend/test_backend.py` startet das Backend im Testmodus und prüft Cosmetics/Accessoires, Codes, Anfragen, Annehmen/Ablehnen,
Stats und den Freundes-Schutz. Der Java-Integrationstest (`tools/BackendIntegrationTest.java`) prüft die Client-API gegen das echte Backend.

## Update 3.9.1: Echte Emote-Vorschau, Kopieren und Einfügen

- **Emote-Vorschau** im Goon Shop und Inventar zeigt jetzt deinen echten Minecraft-Spieler (Skin, Rüstung, Cape, Accessoires) als 3D-Modell in
  der Emote-Pose, genau wie Minecrafts Inventar-Vorschau. Die Pose kommt über dieselben Eingriffe wie im Spiel, sieht also exakt so aus wie das Emote in der Welt.
  Die alte 2D-Strichfigur ist entfernt.
- **Alle Textfelder** (Redeem code, Friends, Suche, Waypoints, Crosshair-Editor): **STRG+V** einfügen, **STRG+C** kopieren, **STRG+X** ausschneiden,
  **STRG+A** alles markieren (Tippen ersetzt dann den Text), **STRG+Rücktaste** löscht ein Wort. Eingefügte Zeilenumbrüche werden zu Leerzeichen,
  Leerzeichen am Rand fallen weg. Umgesetzt in `gui/widget/TextInput.java`.

## Update 3.9.2: Emote-Karten zeigen jeweils ihr eigenes Emote

Fehler in 3.9.1: Im Shop sahen alle Emote-Karten gleich aus. Ursache: Minecraft hat für Entities im Menü nur einen Renderer mit einer Textur;
bei mehreren Spieler-Vorschauen im selben Bild landeten alle in derselben Textur und zeigten das Bild der zuletzt gezeichneten.
`GuiRendererMixin` gibt jetzt jeder weiteren Entity-Vorschau eines Bildes einen eigenen Renderer (Pool, höchstens 32 extra). Vanilla-Bildschirme
mit nur einer Vorschau laufen wie bisher.

## Update 3.9.3: Emotes mit anderen Animations-Mods (Not Enough Animations)

Fehler: Bei installiertem **Not Enough Animations** (und ähnlichen Mods) standen die Arme bei allen Emotes gleich, im Shop und in der Welt;
nur Kopf und Körperdrehung stimmten. Ursache: Not Enough Animations setzt die Spieler-Arme am Ende von `PlayerModel.setupAnim` neu, also nach der
Emote-Pose. Fix:
- `PlayerModelMixin` wendet die Emote-Pose am Ende von `PlayerModel.setupAnim` mit hoher Priorität an, also nach solchen Mods (Spieler und Rüstung).
- Während eines Emotes **führt** die Pose die Arme (`EmotePoseApplier`, weich ein- und ausgeblendet), statt nur auf die fremde Armhaltung
  zu addieren. Dadurch sieht ein Emote auch mit einem Item in der Hand immer gleich aus.
- Die Shop-Vorschau zeigt das Emote durchgehend in voller Pose (keine Pause in der Grundhaltung mehr zwischen den Durchläufen).

Getestet im Spiel mit Not Enough Animations 1.12.6, Netherite-Rüstung und Schwert, und ohne den Mod: alle 10 Vorschauen und 6 Emotes in der Welt.

## Update 3.10.0: Codes ohne neue Mod-Version

Codes prüft jetzt das **Backend**. Neue Codes trägst du nur noch auf dem Server ein, die Spieler brauchen **keine neue Version** des Goon Clients.

### Neuen Code anlegen (3 Schritte)
1. Im Projektordner: `py -3 tools/backend/add_code.py 500` (500 = Anzahl Coins). Das Skript zeigt den neuen Code an (z.B. `GOON-AB12-CD34`)
   und trägt ihn in `tools/backend/codes.json` ein. **Den angezeigten Code aufheben**, in der Datei steht nur ein Hash.
2. `tools/backend/codes.json` auf GitHub hochladen (die Datei im Repo ersetzen).
3. Render deployt automatisch neu. Danach gilt der Code sofort für alle Spieler.

Optionen: `--code GOON-MEIN-CODE` (eigener Code), `--max-uses 20` (nur die ersten 20 Spieler), `--expires 2026-12-31` (gültig bis einschließlich),
`--list` (alle Codes anzeigen). Läuft der Server dauerhaft, liest er geänderte `codes.json` sogar ohne Neustart neu ein.

### Verhalten
- Jeder Code gilt pro Minecraft-Account nur einmal (das Backend merkt es sich), zusätzlich lokal pro Konto.
- Meldungen: ungültig, schon eingelöst, abgelaufen, aufgebraucht.
- Ohne Online-Sync (Offline-Konto, Server nicht erreichbar) oder mit einer alten `server.py` gelten nur die fest eingebauten Codes
  (`GOON-9GAT-ZTY7`, `GOON-3PCM-YPJY`).
- **Einmalig nötig:** dieses Client-Update 3.10.0 verteilen und die neue `server.py` + `codes.json` auf Render einspielen. Ab dann nie wieder für Codes.

## Update 3.11.0: Cape-, Badge- und Nametag-Einstellungen im Inventar

- Die Bereiche **Capes**, **Badges** und **Animated Nametags** sind aus "Goon Cosmetics" entfernt. Dort bleiben Live-Vorschau,
  **Effects & Themes** und **Settings** (was du von anderen siehst, Online-Sync, Diagnose).
- Im **Inventory** gibt es bei Capes, Badges und Nametags unter dem Item einen Bereich **Customize**: Live-Vorschau deines Namens bzw. deiner Cape,
  An/Aus und alle Einstellungen (Badge: Text für das Custom-Badge, Farbe, Position vor/nach dem Namen; Nametag: Farbe 1 und 2, Tempo,
  Animate, Bold). Ausgerüstet wird wie gewohnt mit Equip.
- Beim Öffnen einer Kategorie im Inventar ist das gerade getragene Item ausgewählt.

## Update 3.12.0: Emotes überarbeitet

- **Entfernt:** Laugh, Heart, Cry. Sie sind nicht mehr im Shop und nicht mehr im Inventar. Wer sie gekauft hatte, bekommt den Preis
  automatisch zurück (80 + 100 + 120 Coins) und sieht beim Start eine Meldung. Sie fliegen auch aus dem Emote-Rad.
- **Dab** neu nach dem echten Vorbild: Kopf nach unten in die Ellenbeuge, ein Arm quer vor dem Gesicht, der andere gestreckt schräg nach oben zur Seite.
- **Celebrate → Levitate** (Legendary): im Schneidersitz schweben, Hände auf den Knien, sanftes Auf und Ab. Wer Celebrate hatte,
  besitzt automatisch Levitate (auch im Emote-Rad).
- **Neu: Orange Justice** (Epic, 750 Coins): gebeugte, federnde Knie, Arme pumpen über Kreuz vor dem Körper, Schritte zur Seite,
  am Ende Schulterzucken und Klatschen über dem Kopf.
- Technik: Posen können jetzt auch Arme quer vor den Körper drehen, Beine seitlich bewegen und den ganzen Körper heben/senken (`EmoteEngine`, `EmotePoseApplier`).
- Coin-Datei: Entfernte oder ersetzte Items machen das Konto nicht mehr ungültig. Erst wird unverändert geprüft, dann umgestellt
  (`Wallet.migrate`, `ShopCatalog.RETIRED` / `REPLACED`).
- Backend: `server.py` kennt die neuen Emote-Ids (`orangejustice`, `levitate`). Damit andere Spieler sie sehen, `server.py` neu einspielen.

## Update 3.13.0: Bend-Tool (Ellbogen und Knie) und überarbeitete Emotes

- **Bend-Tool** (`emote/LimbBender`, `ModelPartMixin`): Arme und Beine können sich jetzt in der Mitte **kurvig biegen** (Ellbogen, Knie), wie bei
  Emotecraft/bendy-lib. Die Seitenflächen werden dafür in Scheiben zerlegt und weich um das Gelenk gedreht, die Textur läuft lückenlos mit.
  Gilt für Haut, Ärmel-/Hosen-Overlay und Rüstung. Biegerichtung wählbar (vor/zurück oder seitlich).
- Gehaltene Items folgen dem gebogenen Unterarm. Die eigene Hand in der Ego-Ansicht bleibt immer gerade.
- **Alle Emotes überarbeitet und geglättet**: weiche Keyframes mit Ein- und Ausschwingen (smootherstep), dazu Ellbogen und Knie:
  Wave (Unterarm hoch, winkt aus dem Ellbogen), Salute (Hand an der Stirn), Flex (echter Doppel-Bizeps), Dab (angewinkelter Arm vor dem Gesicht),
  Spin, Dance (angewinkelte Arme, federnde Knie), Orange Justice (gebeugte Knie), Levitate (echter Schneidersitz mit gekreuzten Unterschenkeln).
- Getestet im Spiel ohne und mit Not Enough Animations, mit Netherite-Rüstung und Schwert in der Hand.

## Update 3.14.0: Emotes wie echte Menschen

Jedes Emote nach echten Vorbildern neu aufgebaut. Gebogen wird nur, wo ein Mensch den Arm oder das Bein wirklich beugt:
- **Wave:** Oberarm schräg nach außen oben, Unterarm fast senkrecht; er schwingt wie ein Metronom aus dem Ellbogen, Kopf neigt sich freundlich.
- **Salute:** militärischer Gruß, Oberarm waagerecht, Unterarm im 45°-Winkel, Fingerspitze an der rechten Augenbraue; zackig hoch und ruhig gehalten.
- **Flex:** Front Double Biceps, Oberarme knapp über Schulterhöhe, Ellbogen ~90°, Fäuste zum Kopf, Beine schulterbreit, im Takt angespannt.
- **Dab:** Kopf in der Ellenbeuge, anderer Arm gestreckt schräg nach oben; kleines Ausholen, zweimal Nachnicken.
- **Spin:** Pirouette mit kurzem Schwungholen, ausgebreiteten (geraden) Armen und auslaufender Drehung.
- **Dance:** Two-Step-Groove mit Schritten zur Seite, federnden Knien, gegengleich schwingenden Armen und Gewichtsverlagerung.
- **Orange Justice:** gebeugte, federnde Knie, fast gestreckte Arme kreuzen vor der Hüfte, Kicks zur Seite; Schulterzucken und Klatschen über dem Kopf.
- **Levitate:** Schneidersitz mit gekreuzten Unterschenkeln, Hände locker auf den Knien, ruhiges Schweben.
Alle stehenden Emotes atmen leicht; Übergänge laufen mit weichem Ein- und Ausschwingen.

## Website

Die Website läuft auf demselben Render-Server wie das Backend: **https://goonclient-backend-1.onrender.com/**

- **Inhalt:** Download der neuesten Version, alle Funktionen, die Redeem-Codes zum Kopieren und die Updates (direkt aus diesem
  Changelog), dazu eine Installationsanleitung. Die Seite funktioniert auch auf dem Handy.
- **Dateien:** `tools/backend/site/`
  - `index.html` – die Seite.
  - `downloads/goonclient-x.y.z.jar` – die JAR für den Download-Knopf.
  - `CHANGELOG.md` – eine Kopie dieser README; daraus kommen die Updates und die Versionen von Minecraft und Fabric API.
- **Aktualisiert sich mit dem Client:** Nach jedem `gradlew build` kopiert der Schritt `updateSite` die neue JAR (die alte wird
  gelöscht) und die README automatisch dorthin. Danach den Ordner `tools/backend` (mindestens `site/`) auf GitHub hochladen;
  Render deployt neu und die Website zeigt die neue Version, den neuen Download und die neuen Updates.
- **Codes auf der Website:** Nur Codes mit `"public": true` in `codes.json` erscheinen (dafür steht dort zusätzlich der Klartext).
  Neue öffentliche Codes: `py -3 tools/backend/add_code.py 500 --public`. Abgelaufene oder aufgebrauchte Codes verschwinden
  automatisch. Bei Codes mit Limit zeigt die Seite, wie oft sie noch einlösbar sind.
- **Funktionsliste:** steht oben im Skript von `index.html` (`FEATURES`). Bei großen neuen Funktionen dort eine Zeile ergänzen.
- **Server-Routen:** `/` (Seite), `/download` (neueste JAR), `/v1/site` (Version, Updates, Codes als JSON).
- **Lokal ansehen:** `py -3 tools/backend/server.py --insecure --port 8097`, dann http://localhost:8097 öffnen.

## Update 3.43.1: HUD-Editor ohne Unschärfe

- **Fix:** Im HUD-Editor ("Move HUD elements") war alles weichgezeichnet, auch die Elemente, die man verschiebt. Jetzt bleibt
  alles scharf und in echter Farbe, ohne Abdunklung.
- Die Prozent-Angaben an den Elementen und das Kreuz über den ganzen Bildschirm sind weg. Beim Element unter der Maus
  stehen nur noch sein Name und eine leichte Hervorhebung.
- Der Hinweis zur Bedienung ist eine kleine Leiste oben in der Mitte, die nach ein paar Sekunden ausblendet.

## Update 3.43.0: Halloween-Theme und ruhigeres Menü-Design

- **Neues Theme "Halloween"** (Goon Cosmetics → Themes, mit "SEASONAL"-Markierung):
  - Kürbis-Orange auf Nacht-Lila; das Logo wird zum geschnitzten Kürbis (Seitenleiste und Startseite).
  - Fledermäuse flattern durchs Menü, oben rechts hängt ein Spinnennetz und in der Titelzeile baumelt eine Spinne.
  - Die schwebenden Partikel werden zu aufsteigender Glut in Orange und Lila.
  - Auf der Startseite: "Happy Halloween! Trick or treat." und eine kleine Fledermaus.
- **Cleaneres, weicheres Menü:**
  - Weicher Schatten unter dem Fenster und ein feiner Rand statt der harten Akzent-Kante; die Leuchtlinie oben läuft zu den
    Ecken hin aus.
  - Hintergrund mit sanftem Verlauf statt flacher Abdunklung.
  - Seitenleiste mit kleinen Gruppen-Überschriften ("MODULES", "CLIENT") und einer feinen Kante zum Inhalt; bei kleinen
    Fenstern rückt sie automatisch enger zusammen, damit alle Tabs sichtbar bleiben.
  - Feine Trennlinie unter der Titelzeile, weicherer Seitenwechsel (Ease-out).
  - Theme-Karten heben sich beim Hovern leicht an.

## Update 3.42.0: Automatische Updates

- **Eingebauter Updater:** Ab dieser Version muss man die JAR nicht mehr für jedes Update neu herunterladen.
  - Beim Start schaut der Client auf dem GoonClient-Server nach einer neuen Version (danach alle 3 Stunden).
  - Gibt es eine, erscheint eine kleine Meldung und oben auf der Home-Seite ein Hinweis mit **"Install"** und **"Later"**.
    Installiert wird **nur nach Klick**.
  - Die neue JAR wird im Hintergrund geladen und geprüft: Größe, SHA-256-Prüfsumme und eine digitale **Signatur**. Nur
    Updates, die wirklich vom GoonClient-Entwickler signiert sind, werden installiert.
  - Beim **Schließen von Minecraft** tauscht ein kleiner Helfer die alte JAR gegen die neue; beim nächsten Start läuft die
    neue Version.
  - Klappt der automatische Austausch einmal nicht, zeigt der Client das an, und **"Open folders"** öffnet den Update-Ordner
    und den Mods-Ordner zum Austauschen von Hand.
  - Braucht ein Update eine andere Minecraft-Version, wird es nicht installiert; dann gibt es den Hinweis auf die Website.
- **Settings:** neuer Schalter "Check for updates" und ein Abschnitt **Updates** mit Status, "Check now" und "Install update".
- Diese Version muss **noch einmal von Hand** installiert werden; ab dann kommen Updates automatisch.

> **Für den Entwickler:** Der Build signiert jede JAR mit `~/.goonclient/update-signing.key` (liegt nur auf deinem PC).
> **Diese Datei sichern!** Ohne sie können keine automatischen Updates mehr veröffentlicht werden. Beim Hochladen der Website
> immer den ganzen `site`-Ordner hochladen, auch die `.sig`-Datei in `site/downloads`.

## Update 3.41.0: Armor Durability Overlay und Totem Tweaks

Zwei neue Module (Kategorie **Render**):

- **Armor Durability Overlay:** Rüstung bekommt überall in Hotbar, Inventar, Truhen und Armor-HUD einen farbigen Rahmen:
  **Grün** = (fast) voll, **Gelb** = mittel, **Rot** = fast kaputt.
  - Stil: Rahmen, Hintergrund oder beides; Rahmendicke 1–2, Deckkraft.
  - "Smooth colors" lässt die Farbe fließend von Grün über Gelb nach Rot wechseln.
  - Grenzen einstellbar ("Yellow below", "Red below"); auf Wunsch auch für Werkzeuge und Waffen.
- **Totem Tweaks:**
  - **Kleinerer Totem-Pop:** Die Totem-Animation in der Bildschirmmitte ist kleiner (10–100 %, Standard 50 %) oder ganz aus.
  - **Kein Pop-Sound:** Sound stumm schalten oder leiser machen.
  - **Partikel:** 0–200 % (0 = keine Partikel).
  - **Pop-Nachrichten:** Im Chat steht, wenn ein Spieler ein Totem verbraucht, mit Zähler und seinen Leben, z.B.
    "Steve popped 3 totems (6 HP)". Der Zähler beginnt nach dem Tod oder in einer neuen Welt von vorne. Eigene Pops nur auf Wunsch.

## Update 3.40.0: Item Scale mit Item-Liste

- **Item Scale – eigene Größe pro Item:** In den Einstellungen von Item Scale gibt es den Knopf **"Item list"**. Er öffnet eine
  Liste mit allen Items und Blöcken (alles, was man droppen kann):
  - Suche nach Name oder ID (z.B. "crystal"), Filter **"Changed only"** zeigt nur Items mit eigener Größe.
  - Klick auf ein Item: große Vorschau, Regler **10–1000 %**, Schnellknöpfe (50, 100, 200, 400, 800, 1000 %) und "Reset".
  - Die eigene Größe gilt, wenn das Item auf dem Boden liegt, und hat Vorrang vor "Dropped items size".
  - **End-Kristall:** Die Größe gilt auch für **platzierte** End-Kristalle.
- **"Dropped items size"** geht jetzt bis **1000 %** (vorher 300 %).

## Update 3.39.0: Block Highlight weich, Boden-Items, Modul-Icons

- **Block Highlight:**
  - **Fix:** Die Füllung ("Filled" und "Outline + Fill") hat geflackert und Streifen gezeigt, weil sie genau auf der Blockoberfläche
    lag. Sie liegt jetzt ein winziges Stück davor; das Flackern ist weg.
  - **Weicher Übergang:** Schaust du zu einem anderen Block, gleitet die Hervorhebung zum neuen Block, statt zu springen.
    Einstellbar: "Smooth transition" (an/aus) und "Transition speed".
- **Item Scale:** neue Einstellung **"Dropped items size"** für die Größe von Items, die auf dem Boden liegen (25–300 %).
- **Icons für alle Module:** Jede Modul-Karte (Render, HUD, Utility, Misc, Movement und die Gadgets) hat links ein eigenes
  Pixel-Icon, z.B. Monitor für FPS, Truhe für Inventar, Sanduhr für TPS, Würfel für Hitboxes, Pfeile für Stretched. Das Icon
  leuchtet, wenn das Modul an ist, und bewegt sich beim Hovern.

## Update 3.38.0: Block Highlight, Item Scale, Stretched Resolution

Drei neue Module (Kategorie **Render**):

- **Block Highlight:** der Rahmen um den anvisierten Block in eigener Farbe und Dicke statt dünn und schwarz.
  - Stil: nur Rahmen, nur Füllung oder beides; Füllfarbe und Deckkraft getrennt einstellbar.
  - Linienstärke 1–8, Regenbogen-Modus mit Geschwindigkeit, "Expand" für einen etwas größeren Rahmen.
  - Die Form folgt dem echten Block (Stufen, Halbblöcke, Zäune ...). Mit "Full block box" ist es immer ein ganzer Würfel.
- **Item Scale:** Items in der Hand (Ego-Ansicht) kleiner oder größer (20–200 %) und verschiebbar (X/Y/Z). Die Nebenhand
  (z.B. Totem, Schild) wie die Haupthand oder mit eigener Größe.
- **Stretched Resolution:** Die Spielwelt wird wie auf einem 4:3-Bildschirm gezeichnet und auf die volle Breite gestreckt. Alles
  wirkt breiter, Gegner sind breiter.
  - Zur Wahl: 4:3, 5:4, 3:2, 16:10, 1:1 oder ein eigenes Verhältnis; "Strength" für eine teilweise Streckung.
  - Menüs, Chat und HUD bleiben normal.

## Update 3.37.0: Kein automatischer Stern mehr

- **Fix:** Jeder GoonClient-Spieler hatte ungewollt einen **★ neben dem Namen**, den alle anderen GoonClient-Nutzer sahen. Grund:
  Das Namens-Badge war standardmäßig eingeschaltet, und der erste Stil ist der kostenlose Starter-Stern.
- Das Badge ist jetzt **standardmäßig aus**. Beim ersten Start mit 3.37.0 wird es bei allen einmal ausgeschaltet. Wer ein Badge
  möchte, rüstet es im **Inventar** neu aus und behält es dann.
- Spieler, die noch eine ältere Version benutzen, schicken den Stern weiter, bis sie updaten.

## Update 3.36.0: Pack Mixer – Sounds gehören zum Teil

- Das eigene Abteil "Sounds" ist wieder weg. Sounds aus einem Pack gehören jetzt **direkt zu ihrem Teil**: Wer z.B. die Armbrust aus
  "Goon_makros" wählt, bekommt automatisch auch deren Schuss-Sounds (`item/crossbow/shoot1-3`).
- Zuordnung:
  - `item/<name>/...` gehört zum Item (Armbrust, Streitkolben, Schild ...),
  - `item/armor/equip_<material>` zum Rüstungs-Set,
  - `item/totem/...` zum Totem, `random/bow` zum Bogen,
  - `block/<name>/...` zum Block (z.B. Seelenanker),
  - `fire/...` zum Feuer.
  Andere Sounds werden nicht angezeigt.
- Ein **♪** auf der Karte zeigt, dass ein Pack für dieses Teil Sounds mitbringt. Im Inspector steht bei der Variante z.B.
  "♪ + 3 sounds".
- Ändert ein Pack für ein Teil nur die Sounds, zeigen Karte und Inspector das Vanilla-Bild (mit ♪).
- Die passenden Einträge aus der `sounds.json` kommen beim Bauen weiterhin mit.

## Update 3.35.0: Pack Mixer – Sounds

- Neues Abteil **Sounds**: Hier stehen die Sounds, die deine Texture Packs mitbringen. Es gibt keine feste Vanilla-Liste wie bei den
  anderen Abteilen; ein Sound erscheint nur, wenn ein Pack ihn hat.
- Durchnummerierte Sounds sind ein Paket: z.B. `shoot1`, `shoot2`, `shoot3` der Armbrust = **"Crossbow Shoot"**.
- Beim Bauen kommen die passenden Einträge aus der `sounds.json` des Packs mit, und zwar nur die, die zu den gewählten Sounds
  gehören. Sie werden mit einer vorhandenen `sounds.json` (z.B. aus dem Base Pack) zusammengeführt. So funktionieren auch Packs, die
  Sounds unter eigenem Namen einbinden.
- Abspielen in der Vorschau gibt es noch nicht; die Karte zeigt ein ♪.

## Update 3.34.0: Coin Upgrader günstiger

Ab Upgrade 4 (5 Coins pro Minute) steigt der Preis nur noch um **x1,25** statt x2 (auf 10 gerundet):

| Upgrade | Coins / Minute | Preis vorher | Preis jetzt |
|---|---|---|---|
| 1 | 2 | 250 | 250 |
| 2 | 3 | 500 | 500 |
| 3 | 4 | 1.000 | 1.000 |
| 4 | 5 | 2.000 | 1.250 |
| 5 | 6 | 4.000 | 1.560 |
| 6 | 7 | 8.000 | 1.950 |
| 7 | 8 | 16.000 | 2.440 |
| 8 | 9 | 32.000 | 3.050 |
| 9 | 10 | 64.000 | 3.810 |

Alle Upgrades zusammen kosten jetzt **15.810** statt 127.750 Coins. Bereits gekaufte Upgrades bleiben erhalten.

## Update 3.33.0: Pack Mixer – Ores aufgeräumt

- Im Abteil **Ores** stehen nur noch die Vanilla-Erze: Kohle, Eisen, Kupfer, Gold, Redstone, Smaragd, Lapis, Diamant (je normal und
  Tiefenschiefer), Nethergold-Erz und Netherquarz-Erz (18 Stück).
- Entfernt: antiker Schutt und alle fremden Erze aus Packs (z.B. Zinn), die vorher dahinter erschienen.

## Update 3.32.0: Pack Mixer – Rüstung nur als ganzes Set

- Rüstung gibt es im Pack Mixer jetzt nur noch **als ganzes Set pro Material**: z.B. "Netherite Armor" = Helm, Brustplatte, Hose und
  Stiefel, dazu das Rüstungsmodell am Körper (beide Lagen) und bei Leder die Overlays. Einzelne Teile kann man nicht mehr mischen.
- Abteil "Armor": 8 Sets (Leder, Kettenhemd, Kupfer, Eisen, Gold, Diamant, Netherit, Schildkröte). Jede Karte, die große Vorschau
  und die Varianten im Inspector zeigen alle vier Teile zusammen. Teile, die ein Pack nicht ändert, erscheinen dabei in Vanilla.
- Ältere Auswahlen einzelner Rüstungsteile wandern automatisch zum ganzen Set.

## Update 3.31.0: Pack Mixer – Feuer und Glint

Drei neue Abteile im Pack Mixer, jeweils als ein Paket mit Vanilla und allen Pack-Varianten:

- **Fire:** Feuer (`block/fire_0`, `fire_1`), Seelenfeuer und die Lagerfeuer-Flammen, samt Animationen. Das Feuer am Bildschirmrand,
  wenn man brennt, nutzt dieselbe Textur.
- **Enchant Glint:** der Verzauberungs-Schimmer auf Items (`misc/enchanted_glint_item`, ältere Packs: `enchanted_item_glint`).
- **Armor Glint:** der Verzauberungs-Schimmer auf getragener Rüstung (`misc/enchanted_glint_armor`).

## Update 3.30.0: Pack Mixer – Erze und ihre Items

Zwei neue Abteile im Pack Mixer:

- **Ores:** alle Erze, jeweils normal und als Tiefenschiefer-Variante: Kohle, Eisen, Kupfer, Gold, Redstone, Smaragd, Lapis, Diamant.
  Dazu Nethergold-Erz, Netherquarz-Erz und antiker Schutt (19 Stück).
- **Ore Items:** was die Erze geben, in derselben Reihenfolge: Kohle, Roheisen, Eisenbarren, Rohkupfer, Kupferbarren, Rohgold,
  Goldbarren, Redstone, Smaragd, Lapislazuli, Diamant, Goldnugget, Quarz, Netheritplatten, Netheritbarren (15 Stück).
- Wie bei den anderen Abteilen ist die Vanilla-Textur immer da, die Pack-Varianten stehen daneben.
- Tiefenschiefer-Erze stehen bei "Ores", nicht mehr bei "Deepslate".

## Update 3.29.0: Pack Mixer – nur PvP-Teile, je ein Abteil

Der Pack Mixer zeigt aus jedem Texture Pack **nur noch diese Dinge**, jedes in einem eigenen Abteil (links):

Swords, Axes, Pickaxes, Obsidian, Golden Apples, Hearts, End Crystal, Respawn Anchor, Glowstone, Totem, Bow, Crossbow,
TNT Minecart, Mace, Spears, Ender Pearls, Shield, Cobwebs, Deepslate, Stone, Grass Block, Armor, Inventory GUI.

- **Jede Art davon:** alle 7 Schwerter, Äxte, Spitzhacken und Speere (Holz, Stein, Kupfer, Eisen, Gold, Diamant, Netherit), alle
  29 Rüstungsteile (Leder bis Netherit + Schildkrötenpanzer), Obsidian + weinender Obsidian, goldener + verzauberter goldener Apfel,
  Glowstone + Glowstone-Staub, TNT-Lore + TNT-Block, die Tiefenschiefer- und Stein-Arten.
- **Vanilla ist immer da:** Jedes Abteil zeigt alle Vanilla-Teile, auch wenn kein Pack sie ändert. Die Karte zeigt, was gerade
  gilt (Vanilla oder das gewählte Pack). Im Inspector stehen Vanilla und alle Pack-Varianten nebeneinander.
- **Pakete:** "Hearts" enthält alle Herz-Bilder, "Inventory GUI" das Inventar, das Kreativ-Inventar und die Hotbar. Blöcke mit
  mehreren Seiten (Grasblock oben/seitlich/Schnee, Seelenanker-Ladestufen, TNT oben/unten/Seite) sind je ein Paket.
- Alles andere aus den Packs (Sounds, Mobs, sonstige Items ...) wird nicht angezeigt. Der Status zeigt, wie viele Teile das sind.

## Update 3.28.0: Pack Mixer – Items als Paket

- **Alles, was zu einem Item gehört, ist jetzt ein Paket:** Statt "Bow", "Bow Pulling 0", "Bow Pulling 1", "Bow Pulling 2" gibt es
  eine Karte **"Bow"**. Die Armbrust (Standby, Pulling 0–2, Arrow, Firework) ist ebenfalls eine Karte. Genauso Kompass- und
  Uhr-Bilder, Angel (ausgeworfen), kaputte Elytra, Overlays (z.B. Lederrüstung, Trank), Dreizack in der Hand, Fernrohr usw.
- Wer das Paket aus einem Pack wählt, bekommt alle Bilder und Modelle davon.
- Auf der Karte zeigt ein Abzeichen, wie viele Varianten dazugehören (z.B. "+3"). Im Inspector steht, was im Paket steckt
  ("+ Pulling 0, Pulling 1, Pulling 2").
- Hat ein Paket kein eigenes Hauptbild (Armbrust), zeigt die Vorschau die Ruhe-Variante, auch bei Vanilla.
- Ältere Auswahlen einzelner Varianten (z.B. "Bow Pulling 0") wandern automatisch zum Paket ("Bow").

## Update 3.27.0: Pack Mixer – Vorschau-Fix

- **Fix: Nach "Rescan" fehlten die Vorschauen** (überall "?"). Beim Neu-Einlesen wurde das alte Pack geschlossen, während das Menü
  noch Vorschauen daraus lud. Diese schlugen fehl, und "kein Bild" blieb dauerhaft gespeichert.
  - Die alten Packs bleiben jetzt offen, bis die neue Liste fertig ist. Erst dann werden die Vorschauen neu geladen.
  - Eine Datei, die gerade nicht lesbar ist, wird später erneut versucht statt dauerhaft als "kein Bild" gemerkt.
- Geprüft mit einem echten HD-Pack (512x512): Vorschauen erscheinen beim Öffnen, nach "Build & apply" und nach "Rescan".

## Update 3.26.0: Pack Mixer – zusammengehörige Texturen und schärfere Vorschau

- **Zusammengehörige Texturen bleiben zusammen:** Eine Entity-Textur mit demselben Namen wie ein Item gehört jetzt zu diesem Item.
  Beispiel: `entity/equipment/wings/elytra` (die Flügel am Rücken) gehört zum Item **Elytra**. Wer die Elytra aus einem Pack nimmt,
  bekommt beide Texturen. Ebenso:
  - Rüstungsmodelle (`entity/equipment/humanoid/diamond`, ältere Packs `models/armor/diamond_layer_1`) gehören zur passenden
    Rüstung, z.B. zur Diamantbrustplatte.
  - Pferde- und Wolfsrüstung, der Dreizack usw.
  - Ändert ein Pack nur die Flügel, erscheint trotzdem das Item "Elytra" mit dieser Variante.
- **Vorschau bis 512x512:** Bilder werden nicht mehr auf 32x32 verkleinert, sondern bis 512x512 geladen. Dazu:
  - richtiges Seitenverhältnis statt eines quadratischen Ausschnitts,
  - durchsichtige Ränder werden abgeschnitten (von der Flügel-Textur war vorher nur ein Punkt zu sehen),
  - kleine Pixel-Texturen werden ganzzahlig vergrößert (scharfe Pixel), bei Animationen nur das erste Bild.
  - Die Vorschauen nutzen höchstens 96 MB Speicher; ältere werden automatisch freigegeben.

## Update 3.25.0: Neuer Look für den Pack Mixer

Der Pack Mixer ist komplett neu aufgebaut, als "Style-Archiv":

- **Oben "Your mix":** alle gewählten Teile als Icons. Ein Klick springt zu dem Teil.
- **Links "Groups":** Sammlungen mit Icon und Anzahl: Swords, Tools, Armor, Food & Pearls, Totem, Blocks, Items, Mobs, GUI & HUD,
  Particles, Sky & World, Sounds, Other. Der Reiter **"Packs"** zeigt die Packs; ein Klick zeigt nur die Änderungen dieses Packs.
- **Mitte:** alle Teile als Karten mit Vorschau. "PICKED"-Abzeichen für Teile im Mix, "x styles" bei mehreren Varianten, darunter
  der Name und woher das Teil gerade kommt. Dazu Suche und die Reiter "All" / "★ Picked".
- **Rechts "Inspector":** große Vorschau des angeklickten Teils mit allen Varianten: **Vanilla** (das echte Minecraft-Bild) und jedes
  Pack, das das Teil hat. Hovern zeigt die Variante groß, **Linksklick übernimmt sie**. "ACTIVE" zeigt die aktuelle Wahl.
- **Unten:** Open folder, Rescan, Reset, Base pack, Status, Turn off und der goldene Knopf **"★ Build & apply"**.
- Bei kleinem Menü wird die Liste links zu einer Icon-Leiste (Name beim Hovern). Bei sehr kleinem Menü öffnet sich der Inspector
  als Fenster über den Karten, sobald man eine Karte anklickt.
- Animationen: Karten und Varianten schweben beim Hovern, die Auswahl links gleitet, die Vorschau im Inspector schwebt leicht,
  der Build-Knopf leuchtet.

## Update 3.24.0: Pack Mixer – ein Pack anklicken

- Oben im Pack Mixer stehen jetzt alle eingelesenen Packs. **Ein Klick auf ein Pack zeigt nur die Teile, die dieses Pack anders
  macht als Vanilla** (oder neu hinzufügt). Darunter steht, wie viele das sind und wie viele unveränderte Vanilla-Teile
  ausgeblendet wurden. Nochmal klicken oder "All packs" zeigt wieder alles.
- Das **Base pack** ist jetzt ein eigener Knopf ("Base pack: None", ein Klick wechselt der Reihe nach), damit ein Klick auf ein
  Pack nicht mehr aus Versehen das Base Pack setzt.

## Update 3.23.0: Pack Mixer ohne Vanilla-Kopien

- Viele Resource Packs enthalten eine komplette Kopie der normalen Minecraft-Dateien. Der Pack Mixer vergleicht jetzt jedes Teil mit
  den eingebauten Vanilla-Dateien und **zeigt nur noch Teile, die das Pack wirklich verändert oder neu hinzufügt**.
- Als "unverändert" zählt ein Teil, wenn alle seine Dateien inhaltlich gleich sind: gleiche Bytes, gleiches JSON (Leerzeichen und
  Formatierung egal) oder gleiche Pixel (auch wenn das PNG anders gespeichert ist).
- Der Status zeigt, wie viele unveränderte Vanilla-Teile ausgeblendet wurden.
- Getestet mit einem Pack aus echten 1.21.11-Vanilla-Dateien und einem geänderten Schwert: Nur das Schwert erscheint.

## Update 3.22.0: Pack Mixer

Neuer Tab **Pack Mixer** im Menü: Resource Packs auseinandernehmen und einzelne Teile kombinieren, z.B. das Diamantschwert aus
"Pack 1" und die Spitzhacke aus "Pack 2".

1. Resource Packs (.zip oder Ordner) in den Ordner **`.minecraft/goonclient-packs`** legen (Knopf "Open folder" öffnet ihn).
2. "Rescan" drücken. Jedes Item, jeder Block, jede sonstige Textur (Mobs, GUI, Partikel ...), jeder Sound und jede andere Datei
   der Packs erscheint als eigene Zeile, mit Vorschau aus jedem Pack, das dieses Teil hat.
3. In jeder Zeile auf das Pack klicken, aus dem das Teil kommen soll (nochmal klicken = abwählen). Optional ein **Base pack**
   wählen: Es wird komplett übernommen, die einzeln gewählten Teile kommen darüber.
4. **"Build & apply mix"**: Goon Client baut daraus das Pack **"GoonClient Mix"** im resourcepacks-Ordner, schaltet es ganz oben
   ein und lädt die Ressourcen neu. "Turn mix off" schaltet es wieder aus.

- Zu einem Teil gehört alles, was es braucht: Item-Definition, Modell mit Eltern-Modellen, alle benutzten Texturen und
  Animationen (`.png.mcmeta`). 3D-Items aus Packs funktionieren deshalb auch im Mix. Texturen, die nur zu so einem Modell gehören,
  erscheinen nicht doppelt.
- Filter nach Art (Items, Blocks, Textures, Sounds, Other, Picked) und Suche. Die Auswahl wird gespeichert
  (`config/goonclient/pack-mixer.json`).
- Sicher: Ein vorhandener Ordner "GoonClient Mix", den nicht Goon Client gebaut hat, wird nie überschrieben. Die Quell-Packs
  werden nur gelesen.
- Tests: `tools/PackMixerTest.java` (Teile erkennen, Abhängigkeiten, Kombinieren, Schreiben) und ein Test im Spiel (rotes
  Schwert aus "Red Pack" + blaue Spitzhacke aus "Blue Pack", danach in der Hotbar geprüft).

## Update 3.21.0: Accessoires und Emotes von Spieler zu Spieler

- **Ursache, warum andere Spieler deine Accessoires und Emotes nicht gesehen haben:**
  1. Auf Render lief noch eine **alte `server.py`**, die keine Emotes (und keine Freunde) kennt.
  2. Render leitet alle Anfragen über seinen Proxy weiter. Der Server hielt deshalb **alle Spieler für einen** und gab schnell
     "too many requests" zurück, und Uploads, Abrufe und Logins gingen verloren.
- **Fix im Server:** Auf Render (Umgebungsvariable `RENDER`) wird jetzt automatisch die echte Spieler-Adresse aus
  `X-Forwarded-For` benutzt, also ein eigenes Limit pro Spieler. Außerdem reicht dort als Startbefehl `python server.py`
  (Host und `$PORT` werden automatisch gesetzt).
- **Client:** Emotes anderer Spieler werden schneller abgefragt (alle 2 s) und auch bei langsamer Verbindung noch gezeigt
  (bis 6 s alt). Neue Accessoires anderer Spieler erscheinen nach spätestens 10 s. Ist die `server.py` veraltet, steht das
  als Hinweis im Online-Sync-Status.
- **Wichtig:** Damit es wirkt, die neue `tools/backend/server.py` (und `codes.json`) in dein GitHub-Repository hochladen;
  Render deployt dann neu. Andere Spieler brauchen dafür keine neue Mod-Version, nur einen Client mit Online-Sync.
- Neue Backend-Tests: Emote von Spieler A kommt bei B an, geänderte Accessoires kommen an, Limit pro Spieler hinter dem
  Render-Proxy.

## Update 3.20.0: Vorschau mit deinem Charakter und UI-Upgrade

- **Hüte, Flügel und Accessoires** werden im Shop und im Inventar jetzt an **deinem eigenen Minecraft-Charakter** gezeigt (Skin,
  Rüstung, Cape), statt an einer gezeichneten Figur. Das Item wird genau so gezeichnet wie im Spiel.
  - Hüte: Kopf und Schultern groß.
  - Flügel und Rucksäcke: Rückenansicht.
  - Der Charakter dreht sich langsam hin und her.
- **UI-Upgrade:**
  - Animierte Icons in der Seitenleiste: Das Haus hüpft, das Auge blinzelt, die Münze dreht sich, das Schwert schwingt, die Lupe
    wackelt, der Blitz flackert. Das geschieht beim Hovern und leicht beim aktiven Tab.
  - Die Auswahl in der Seitenleiste gleitet weich zum neuen Tab, mit leuchtendem Balken. Beim Hovern rutscht die Beschriftung ein
    Stück nach rechts.
  - Buttons heben sich beim Hovern mit Schatten an und blitzen beim Klick kurz auf. Schalter bekommen einen Schein und einen
    "Gummi"-Effekt.
  - Shop- und Statistik-Karten schweben beim Hovern hoch. Epic- und Legendary-Items leuchten und haben einen wandernden
    Lichtstreifen.
  - Der Seitentitel gleitet beim Wechsel herein. Logo mit Glanz-Effekt. Die Münze im Shop dreht sich, der Coin-Balken läuft weich.
  - Die Startseite hat ein schwebendes, leuchtendes Logo und Statistik-Karten mit animierten Icons und Fortschrittsbalken.
  - Abschnittsüberschriften haben eine Akzent-Markierung.

## Update 3.19.0: Hourly Shop

- Der Goon Shop heißt jetzt **Hourly Shop**. Statt aller Items auf einmal gibt es **jede volle Stunde 5 neue Items**. Ein Countdown
  zeigt, wann der nächste Wechsel kommt.
- Für jeden der 5 Plätze wird zuerst die Seltenheit gezogen, dann ein Item dieser Seltenheit (kein Item doppelt):

  | Seltenheit | Chance pro Platz |
  |---|---|
  | Common | 45 % |
  | Uncommon | 27 % |
  | Rare | 15 % |
  | Epic | 9 % |
  | Legendary | 4 % |

- Kaufen kann man nur, was gerade im Shop ist. Gekaufte Items bleiben für immer im Inventar, auch wenn sie den Shop verlassen.
- Alle Spieler sehen zur selben Stunde (UTC) denselben Shop; ein Neustart würfelt nicht neu (`shop/ShopRotation.java`).
  Der Wechsel richtet sich nach der Uhr des eigenen PCs.
- Oben stehen jetzt die 5 Items und die Vorschau; Coin Upgrader und Code-Feld sind darunter.
- Neuer Test: `tools/RotationLogicTest.java` (20.000 Stunden simuliert: Seltenheiten kommen so oft wie ihre Chance).

## Update 3.18.0: Coin Upgrader

- **Goon Shop → Coin Upgrader:** Damit verdienst du mehr Coins pro Minute, in 9 Stufen von **1 bis 10 Coins pro Minute**:

  | Upgrade | Coins / Minute | Preis |
  |---|---|---|
  | 1 | 2 | 250 |
  | 2 | 3 | 500 |
  | 3 | 4 | 1.000 |
  | 4 | 5 | 2.000 |
  | 5 | 6 | 4.000 |
  | 6 | 7 | 8.000 |
  | 7 | 8 | 16.000 |
  | 8 | 9 | 32.000 |
  | 9 | 10 | 64.000 |

  Zusammen kosten alle Upgrades 127.750 Coins. Jeder Kauf wird mit einem zweiten Klick bestätigt und sofort gespeichert. Die Stufe
  steht signiert in `wallet.json`; wer sie in der Datei von Hand hochsetzt, macht die Datei ungültig.
- Die Meldung beim Verdienen zeigt die echte Zahl ("+5 Goon Coins"). "Du brauchst noch ... Minuten" rechnet mit deiner Rate.
- Der Schalter in den Settings heißt jetzt kurz **"Coin Notification"** (der lange Name wurde abgeschnitten). Dadurch steht er nach dem
  Update einmal wieder auf **an**.
- Hinweis: Eine `wallet.json` mit Upgrades lässt sich in älteren Versionen (vor 3.18.0) nicht mehr laden.

## Update 3.17.0: Orange Justice entfernt, Schalter für die Coin-Meldung

- **Orange Justice** ist komplett entfernt: Man kann es nicht mehr kaufen und nicht mehr im Inventar haben. Wer es gekauft hatte, bekommt
  die **750 Coins zurück**, und es verschwindet automatisch vom Emote-Rad (`ShopCatalog.RETIRED`).
- **Settings → General → "'+1 Goon Coin' Notification":** schaltet die kleine Meldung aus oder an, die jede Minute beim Verdienen einer
  Coin oben erscheint. Die Coins gibt es weiterhin; nur die Meldung fällt weg. Der Schalter war vorher im HUD-Modul "Goon Coins" versteckt.

## Update 3.16.0: Orange Justice zeitgleich wie im Video

- **Orange Justice** neu gebaut und Bild für Bild zur gleichen Zeit mit dem Vorbild-Video verglichen (Durchlauf 6,6 s):
  - **0–4 s aufrecht:** starke Körperdrehung (~50°) zu jedem Knie-Kick zur Seite, Oberarme weit raus, Unterarme pumpen.
  - **ab ~4,1 s Vorbeugen:** Oberkörper weit nach vorne, ein Bein weit zur Seite gestreckt, Arme ausgebreitet.
  - **ab ~4,8 s tiefe Hocke:** Knie weit nach außen, Kopf nach unten, Arme schwingen und gehen einmal weit raus.
  - **zum Schluss:** wieder aufrichten.

## Update 3.15.0: Dab, Levitate und Orange Justice nach Vorgabe

- **Dab:** der rechte Arm (quer vor dem Gesicht) ist jetzt gerade, nicht mehr gebogen.
- **Levitate:** im Schneidersitz biegen die Unterschenkel nach **innen** zur Körpermitte (vorher nach außen).
- **Orange Justice** nach dem Vorbild-Video neu (Durchlauf ~6,2 s): aufrecht mit fast waagerechten Oberarmen, die Unterarme pumpen
  abwechselnd hoch und runter, Knie-Kicks zur Seite; dann tiefe Hocke mit vorgebeugtem Oberkörper, Kopf nach unten, Knie weit nach außen,
  Arme schwingen davor und werden einmal weit ausgebreitet; danach wieder aufrichten.
- Neu in der Emote-Technik: **Vorbeugen ab der Hüfte** (`lean`); die Beine bleiben dabei senkrecht.