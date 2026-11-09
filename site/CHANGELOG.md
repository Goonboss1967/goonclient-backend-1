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

Optionen: `--code GOON-MEIN-CODE` (eigener Code), `--max-uses 20` (nur die ersten 20 Spieler), `--expires 2026-11-05` (kürzer gültig, höchstens 7 Tage ab heute; ohne Angabe genau 7 Tage),
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

- **Inhalt:** Download der neuesten Version, Überblick, **jedes Modul im Detail** (Reiter Render & PvP, HUD, Utility, Gadgets,
  Menü & Client), ein eigener Abschnitt für den **Pack Mixer** (Anleitung, Funktionen, alle Abteile), **Shop & Pass**
  (Goon Coins, Battle Pass, tägliche Belohnung, Missionen, Hourly Shop, Event-Shops, Wunschliste, Outfits), **Freunde**
  (Anfragen, Stats, Geschenke, Emotes, Cosmetics-Sync), die Redeem-Codes zum Kopieren, die Updates (direkt aus diesem
  Changelog), Installation und FAQ. Die Seite funktioniert auch auf dem Handy (Menü-Knopf statt Navigationsleiste).
- **Neue Client-Funktion auf der Website ergänzen:** in `index.html` im Skript die Listen `OVERVIEW`, `MODULES` bzw. die
  Karten in `economy-grid` / `social-grid` erweitern. Codes, Updates, Version und Download kommen automatisch vom Server.
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
- **Server-Routen:** `/` (Seite), `/download` (neueste JAR, `?mc=<version>` für eine bestimmte Minecraft-Version),
  `/v1/site` (Version, Downloads je Minecraft-Version, Updates, Codes als JSON).
- **Lokal ansehen:** `py -3 tools/backend/server.py --insecure --port 8097`, dann http://localhost:8097 öffnen.

## Update 3.97.0: Daten gehören zum Konto (geteilte Modpacks)

**Problem:** Wer sein Modpack an Freunde weitergab, gab den Ordner `config/goonclient` mit. Beim Freund hielt GoonClient 3.96.0
diese Daten für seine eigenen und zog sie in seinen Konto-Ordner um: Er hatte danach dieselben Coins, Cosmetics, Outfits und
Freunde. Das ging schon vor 3.96.0 so, weil die Daten einfach in der Instanz lagen.

**Lösung:** Daten werden jetzt einem Minecraft-Konto zugeordnet.
- **Markierung:** Jeder Konto-Ordner bekommt eine `owner.json` mit dem Konto-Schlüssel. Auch der alte Instanz-Ordner, aus dem
  umgezogen wurde, wird so markiert. Wird ein Modpack später weitergegeben, erkennt der Client des Freundes die Daten als fremd
  und übernimmt sie nicht. `owner.json` wird beim Kopieren nie mitgenommen.
- **Unmarkierte alte Daten:** Steht der aktuelle Spieler selbst in der Freundesliste dieser Daten, sind es die Daten eines anderen
  (niemand ist sein eigener Freund). Das trifft den typischen Fall: Man teilt das Modpack mit einem GoonClient-Freund.
- **Wer schon betroffen ist:** Beim Start wird auch der eigene Konto-Ordner geprüft. Fremde Daten (Markierung eines anderen Kontos
  oder man selbst in der Freundesliste) werden nach `foreign/<zeit>` verschoben, nicht gelöscht. Danach startet der Spieler mit
  einem eigenen Konto. Gibt es in anderen Launchern eigene ältere Daten, werden die zurückgeholt; sonst beginnt er frisch. Im Spiel
  erscheint ein Hinweis.
- **Bei der Suche in anderen Launchern** werden fremde Daten nie übernommen; eigene markierte Daten haben Vorrang vor unbekannten.
- **Knopf „Not my data“** in Einstellungen > Your data: legt die Daten beim nächsten Start beiseite. Er ist für den Fall gedacht,
  dass sich fremde Daten nicht automatisch erkennen lassen (unmarkiert, und man stand nicht in der Freundesliste). Er lässt sich
  abbrechen, und ein Import hebt ihn auf.
- **Tests:** `tools/DataStorageTest` prüft das geteilte Modpack, bereits kopierte Daten, Markierungen, die Rangfolge, den Knopf
  und den Import.

**Grenzen:**
- Unmarkierte Daten aus einem schon früher geteilten Modpack, in deren Freundesliste man nicht steht, lassen sich nicht automatisch
  erkennen. Dafür gibt es den Knopf.
- Coins, die der Freund mit den kopierten Daten verdient hat, lassen sich davon nicht trennen und liegen mit unter `foreign/`.
- Freundschaftsanfragen, die der Client des Freundes mit der kopierten Liste schon verschickt hat, bleiben offen, bis sie
  abgelehnt werden.

## Update 3.96.0: Daten überleben Launcher-Wechsel und Modpack-Updates

**Problem:** Coins, gekaufte Items, Outfits, Wunschliste und Einstellungen lagen bisher in `config/goonclient` der jeweiligen
Minecraft-Instanz. Wer den Launcher wechselte oder seine Instanz (z.B. in der Modrinth App) aktualisierte, bekam einen neuen,
leeren Ordner und hatte alles verloren.

**Lösung:** Die Daten liegen jetzt in einem festen Ordner des Benutzers, getrennt pro Minecraft-Konto (UUID):
- Windows: `%APPDATA%\GoonClient\accounts\<uuid>`
- macOS: `~/Library/Application Support/GoonClient/accounts/<uuid>`
- Linux: `$XDG_DATA_HOME/GoonClient/accounts/<uuid>` (sonst `~/.local/share/...`)
- Ändern lässt er sich mit `-Dgoonclient.home=<ordner>` oder der Umgebungsvariable `GOONCLIENT_HOME`.

Jeder Launcher und jede Instanz auf demselben Rechner mit demselben Konto benutzt damit dieselben Daten. Nur der Updater-Ordner
(`update/`) bleibt in der Instanz, weil die JAR in deren `mods`-Ordner liegt.

- **Umzug beim ersten Start:** Die Daten der aktuellen Instanz werden in den neuen Ordner kopiert. Die alten Dateien bleiben
  unverändert liegen.
- **Verlorene Daten zurückholen:** Hat die aktuelle Instanz keine oder kaum Daten (unter 60 verdienten Coins und unter einer
  Stunde Spielzeit), durchsucht GoonClient die Instanzen der bekannten Launcher nach alten GoonClient-Daten und übernimmt die mit
  dem meisten Fortschritt. Durchsucht werden: offizieller Launcher, Modrinth App, CurseForge, Prism Launcher (auch Flatpak), PolyMC,
  FTB App, GDLauncher und ATLauncher. Im Spiel erscheint dann „Your coins and items were restored“. Eine Instanz mit echtem
  eigenem Fortschritt wird nie ersetzt (z.B. bei einem fremden Konto auf demselben PC).
- **Einstellungen > Your data:** zeigt den Speicherort, öffnet den Ordner und findet GoonClient-Daten aus anderen Launchern
  (Coins, Items, Spielzeit, letztes Speichern). „Import“ übernimmt sie beim nächsten Start; der aktuelle Stand wird vorher nach
  `backups/before-import-…` gesichert. Ein geplanter Import lässt sich abbrechen. Der Import passiert erst beim Neustart, weil das
  laufende Spiel die Dateien beim Beenden sonst wieder überschreiben würde.
- **Tägliche Sicherung:** einmal pro Tag eine Kopie in `backups/<datum>`, die letzten sieben bleiben.
- **Zwei Fenster gleichzeitig:** Der Datenordner wird gesperrt. Ein zweites Fenster mit demselben Konto zeigt die Coins nur an:
  Es verdient keine Coins, kauft nichts, holt keine Geschenke ab und speichert das Konto nicht. So überschreiben sich zwei
  Fenster nie gegenseitig.
- **Rückfall:** Ist der feste Ordner nicht beschreibbar, bleibt alles wie früher in der Instanz, mit Hinweis im Spiel.
- **Neue Klassen:** `data/DataHome` (Pfade, Konto, Launcher-Suche), `data/DataMigration` (Umzug, Wiederherstellen, Import,
  Sicherungen), `data/DataStore` (Start, Sperre). Tests: `tools/DataStorageTest`.

**Grenze:** Die Daten liegen weiter nur auf diesem PC. Auf einem anderen Rechner sind sie nicht da; dafür bräuchte es eine
Sicherung im Backend.

## Update 3.95.0: Glas-Look nach Vorlage

Die Oberfläche wurde nach dem Vorlagebild (lila Glas-Menü mit Kirschblüten) überarbeitet. Wie bei 3.94.0 gilt: nur Oberfläche,
Themes und alle Farben kommen weiter aus dem gewählten Theme (die Vorlage ist in Goon Purple am nächsten dran).

- **Formensprache:** Standard sind jetzt weiche, runde Ecken („Corners: Rounded“). Panels sind leicht durchscheinend, haben oben
  einen Hauch Akzentfarbe, eine feine Lichtkante und ein weiches Leuchten am Rand („Glass Effect“, abschaltbar). Die Fasen-Optik
  aus 3.94.0 gibt es weiter unter „Corners: Chamfered“. Die Einstellung heißt neu „Corners“, deshalb starten alle mit dem runden
  Stil; das Raster („Background Grid“) ist standardmäßig aus.
- **Aufbau:** äußerer Rahmen mit leuchtender Kante, darin zwei getrennte Glas-Panels: Navigation links, Inhalt rechts.
- **Logo:** Krone und „GoonClient“ in der Script-Schrift mit leuchtendem Bogen und funkelnden Sternen. Ein Klick darauf zeigt wieder
  „What's New“. In der schmalen Navigation nur die Krone. Fehlt die Script-Schrift, nimmt es die Standardschrift.
- **Navigation:** größere Zeilen, die aktive Seite als leuchtende Fläche mit Verlauf in Akzentfarbe, weicher Hover.
- **Fenster-Knöpfe** rechts in der Kopfzeile: „–“ klappt die Navigation auf Icons ein und wieder aus (bleibt gespeichert, solange
  das Spiel läuft), „x“ schließt das Menü.
- **Startseite neu:** Begrüßung („Welcome back, Name!“) mit kleiner Nachtszene (Mond, Torii, Pagode, Bäume, Kirschblüten),
  Schnellzugriffe Modules / Cosmetics / Shop, Banner zum Battle Pass, rechts „Client Info“ (Version, FPS, Module, Online-Status)
  und „Quick Settings“ (Animations, Particles, Blossoms, Glass Effect). Bei schmalem Inhalt stehen die rechten Karten darunter.
- **Kirschblüten:** Blütenzweige an den Rahmenkanten (nie über Text) und fallende Blütenblätter statt der Punkt-Partikel
  („Blossom Decor“, abschaltbar; die Blätter gehören zum Effekt „Floating Particles“). Bei Halloween bleibt die Halloween-Deko.
  Bei „Reduce Animations“ stehen die Blätter still.
- **Bausteine:** Schalter als Pille mit rundem Knopf und Leuchten, Slider mit runder Spur und rundem Knopf, Primär-Buttons mit
  Verlauf und Leuchten, runde Icon-Buttons, Felder mit Leuchten beim Tippen, Chips und Badges als Pillen, Abschnittstitel mit
  leuchtendem Strich. Neue Bausteine in `UiContext`: `glassPanel`, `glow`, `gradient`, `pill`, `roundOutline`.
- **Neue Icons:** Krone, Stern, Herz, Blitz, Pfeil, Minus, Funkeln.
- **Neue Klassen:** `gui/Logo`, `gui/BlossomDecor`. Layout (`UiLayout`) kennt jetzt das Inhaltspanel (`main`) und das Einklappen
  der Navigation (`collapseNav`); beides ist in `tools/UiDesignTest` getestet.

## Update 3.94.0: Neue Benutzeroberfläche („Kommandobrücke“)

Das Menü ist komplett neu gestaltet. Geändert wurde nur die Oberfläche: Themes, Theme-Auswahl, gespeicherte Theme-Namen,
Module, Netzwerk und Spiellogik sind unverändert. Alte Configs, Tastenbelegungen und HUD-Positionen laden weiter.

### Aufbau
- **Navigation links, in Gruppen:** *Game* (Home, Modul-Kategorien, Gadgets, HUD Editor, Waypoints, Pack Mixer),
  *Cosmetics* (Goon Cosmetics, Inventory, Goon Shop, Event-Shops, Battle Pass, Missions), *Social* (Friends, Chat),
  *System* (Settings, **Themes** – neu, About). Die Auswahl gleitet zum aktiven Eintrag; der HUD Editor ist ein eigener Eintrag.
- **Kopfzeile:** Seitentitel mit Untertitel, globale Suche, Coin-Anzeige, Online-Status (Form + Farbe), feine Akzentlinie.
- **Fußzeile:** Version und Tastenhinweise.
- **Kompakte Ansicht:** Ist das Fenster logisch kleiner als 620 × 320 Pixel (große GUI-Skalierung, kleines Fenster), zeigt die
  Navigation nur Icons (Name als Tooltip) und die Fußzeile entfällt. Unter 300 × 200 wird gescrollt statt gestaucht.
- **Formensprache:** Flächen mit zwei abgeschrägten Ecken, feine Linien mit Marken, Eck-Klammern an Hauptpanels, dezentes Raster
  im Hintergrund (abschaltbar), 4-Pixel-Raster, Abschnittstitel in gesperrten Großbuchstaben, neuer einheitlicher Icon-Satz (9 × 9).

### Bedienung
- **Suche (Strg+F):** findet Seiten, Module, Gadgets und Einstellungen; Treffer werden markiert. ↑/↓ wählt, Enter springt hin
  (bei Modulen öffnet sich gleich das Einstellungs-Panel), Esc schließt. Die Modul-Ergebnisseite bleibt wie bisher.
- **Tastatur:** Tab / Shift+Tab und die Pfeiltasten bewegen einen sichtbaren Fokusrahmen, Enter/Leertaste löst aus,
  Esc schließt zuerst Overlays, dann den Fokus, dann das Menü. Die Menütaste und alle Keybinds bleiben wie gehabt.
- **Rechtsklick auf eine Modulkarte:** Kontextmenü mit Ein/Aus, Einstellungen zeigen, Einstellungen zurücksetzen
  (mit Bestätigungsdialog).

### Einstellungen der Oberfläche (Settings oder Themes)
| Einstellung | Werte | Standard |
|---|---|---|
| Menu Size | 50–150 % (deckt die gewünschten 80–140 % ab; der alte Bereich bleibt, damit gespeicherte Werte gültig sind) | 100 |
| Density | Compact / Normal / Airy (Compact blendet die Hilfetexte unter Einstellungen aus) | Normal |
| Corner Style | Chamfered (abgeschrägt) / Rounded | Chamfered |
| Grid Background | an/aus | an |
| Reduce Animations | an/aus: keine Lichtpunkte, keine Icon-Bewegung, keine Partikel, kürzere Übergänge | aus |
| Animation Speed | 50–200 % | 100 |

Die Werte stehen in der bestehenden Config; fehlen sie (alte Config), gelten die Standardwerte.

### Themes und Farben
- Alle Farben werden aus den sechs Theme-Farben abgeleitet (`gui/design/UiPalette`): Flächen, Linien, Hover, Fokus, Schatten,
  Schrift auf Akzent. Text wird bei Bedarf so weit aufgehellt/abgedunkelt, bis er den Mindestkontrast erreicht (4,5 für Text,
  3,0 für gedämpften Text) – auch auf hellen und kontrastarmen Themes. Die Theme-Definitionen selbst sind unverändert.
- Feste Farben gibt es nur noch für Bedeutungen: Erfolg, Warnung, Fehler, Info, Münz-Gold, Favorit (`UiPalette.SUCCESS` …),
  dazu Seltenheitsfarben, Event-Farben, Halloween-Deko und Inhalte wie Fadenkreuz-Farbvorgaben oder Waypoint-Farben.
  Im Menü werden auch diese semantischen Farben pro Theme auf lesbaren Kontrast gebracht (`ui.pal.success` …).
- Zustände sind nie nur farbcodiert: Marker haben Formen (Raute = an, Ring = aus, Strich = Taste, Dreieck = Warnung, X = Fehler),
  der Schalter zeigt einen Strich bzw. einen hohlen Knopf.

### Seiten und Fenster, die angepasst wurden
Hauptmenü (`ClientScreen`, Navigation, Kopf-/Fußzeile, Suche), Home, alle Modul-Kategorien, Gadgets, Suchergebnisse, Modul-Panel,
Waypoints, Pack Mixer, Goon Cosmetics, Inventory, Goon Shop, Event-Shop (Halloween), Battle Pass, Missions, Friends, Chat, Settings,
**Themes (neu)**, About, Update-Fenster (`UpdatePopup`), What's New, HUD Editor (Eck-Griffe, Raster und Mittellinien beim Ziehen),
Emote-Rad, Rechner, Fadenkreuz-Editor, Item-Größen, Chat-Overlay und Chat-Banner, Coin-Anzeige und Toasts.
Die Ausgabe der HUD-Module im Spiel ist unverändert.

### Eigene Seiten und Bausteine bauen
- **Seite:** von `gui/pages/Page` erben und `renderContent(ui, x, y, w)` implementieren (Rückgabe = Höhe); Scrollen, Zuschneiden
  und Rand macht die Basisklasse. Abschnittstitel mit `sectionTitle(...)`. In `ClientScreen.buildTabs()` eine Zeile `addTab(...)`
  ergänzen (Gruppe als letzter Parameter). Die Schnittstelle von `Page` ist unverändert.
- **Bausteine** (alle in `gui/UiContext`): `panel`, `card` (Zustände NORMAL/SELECTED/LOCKED/HIGHLIGHT), `sectionTitle`, `divider`,
  `chip`, `badge`, `marker`, `progress`, `tooltip`, `contextMenu`, `confirm`, Knöpfe (`button` mit PRIMARY/SECONDARY/TEXT/DANGER,
  deaktiviert, lädt), `primaryButton`, `dangerButton`, `iconButton`, `toggle`, `slider` (Wertfeld + Feinschritte), `field`,
  `segments`, `dropdown`. Einstellungen zeichnet `SettingRenderer` automatisch (Name links, Wert rechts, Beschreibung darunter).
- **Maße** stehen zentral in `gui/design/Design` (Raster, Fasen, Höhen, Animationszeiten), das Layout rechnet `gui/design/UiLayout`
  (reines Java, getestet), die Suche `gui/design/SearchIndex`.

### Grenzen
- Eine Mehrfachauswahl-Komponente und eine Drag-Sortierliste gibt es noch nicht als allgemeinen Baustein (keine Seite braucht sie bisher).
- Kein Offline-Vorschau-Renderer: `UiContext` zeichnet über `GuiGraphics` und die Minecraft-Schrift; ein Java2D-Nachbau wäre ein
  zweiter Renderer, der vom echten Bild abweichen würde. Stattdessen: reine Layout-/Farbtests (`tools/UiDesignTest`) und
  Screenshots aus dem Fabric-Client-Spieltest.
- Mixins wurden nicht geändert.

## Update 3.93.0: Geheimnisvolles What's New

Die Einträge im Fenster „What's New“, das nach einem Update aufpoppt, bestehen für die geheimen Updates (3.91.0 bis 3.93.0) nur noch aus Fragezeichen, Überschrift und Text. Was wirklich neu ist, steht hier in der README.

## Update 3.92.0: Feinschliff für geheime Items

- **Effekte der Seltenheit ???:** wenige, langsam aufsteigende Fragezeichen in Violett und Weiß, ein weicher Lichtpunkt bei besonderen Momenten und ein Namensschild mit wanderndem Violett-Grau-Verlauf. Alles abschaltbar (Effekte, Namensschild), mit festen Obergrenzen und Level of Detail: ab 32 Blöcken weniger, ab 64 Blöcken nichts.
- **Haustiere allgemein:** höchstens 24 werden gezeichnet, die nächsten Spieler zuerst.
- **Einstellungen geheimer Items** erscheinen erst nach der Freischaltung. Einige davon gelten nur auf dem eigenen Bildschirm, weil das Netz-Paket der Haustiere dafür keinen Platz hat; das Backend musste dafür nicht geändert werden.
- **Synchronisierung:** Die Id läuft über das vorhandene Haustier-Feld (`^[a-z0-9_]{0,24}$`), Client und Backend nehmen sie ohne Änderung an. Der Code wird nie übertragen, unbekannte Ids bei anderen Spielern werden still ignoriert. Fremden Besitz kann niemand prüfen.

## Update 3.91.0: Seltenheit ??? und geheime Items

Es gibt eine neue, siebte Seltenheit: **???**. Sie steht über Legendary und über Exclusive, wird überall als „???“ angezeigt und hat einen dunklen violett-schwarzen Rahmen, an dessen Kante langsam ein helles Licht entlangläuft. Die fünf normalen Stufen, ihre Preisbänder, Exclusive und alle gespeicherten Daten bleiben unverändert, alte Wallets laden wie bisher.

„???“-Items haben keinen Preis, kommen nie in den Goon Shop oder Hourly Shop, stehen in keiner Liste und auf keiner Wunschliste. Vor der Freischaltung zeigt die Oberfläche nichts davon. Freigeschaltet werden sie nur über das vorhandene Exclusive-Code-System. Danach öffnet sich das Inventar mit dem Item und dem Effekt „??? unlocked“.

### Eigenen Code einrichten
Der Code wird im Backend geprüft, in `codes.json` steht nur ein Hash. Im Projekt, in Tests und Logs steht kein echter Code; Tests nutzen nur einen klar markierten Testwert.
1. Im Projektordner einen Code anlegen. Zufällig (empfohlen):
   ```bash
   py -3 tools/backend/add_code.py 0 --item <item-id> --max-uses 1
   ```
   Oder einen eigenen Wunsch-Code verdeckt eintippen (steht dann nicht in der Shell-Historie und wird nicht ausgegeben):
   ```bash
   py -3 tools/backend/add_code.py 0 --item <item-id> --max-uses 1 --ask
   ```
   Nur den Hash ausrechnen, ohne etwas einzutragen: `py -3 tools/backend/hash_code.py`. Kurze Codes lassen sich aus dem Hash erraten, besser 12 Zeichen oder mehr.
2. `tools/backend/codes.json` im Backend-Repo ersetzen und auf Render deployen.
3. Innerhalb von 7 Tagen im Goon Shop unter **Redeem code** einlösen. Die Freischaltung bleibt danach dauerhaft in `wallet.json`.

### Auf normalen Shop-Kauf umstellen
Ein Schalter in `ShopCatalog`: `SECRET_ITEMS_FOR_SALE = true` macht alle „???“-Items zu normalen Shop-Items für `SECRET_SHOP_PRICE` Coins (Standard 3000), mit 1 % Chance pro Platz im stündlichen Goon Shop. Bei `false` (Standard) gibt es sie nur per Code.

### Schutz, ehrlich
- **Der Code wird im Backend geprüft**, nicht im Client. Wer den Programmcode liest, findet ihn nicht. `--max-uses 1` lässt nur ein Konto einlösen.
- **Der Besitz liegt danach im Client** (`wallet.json`, gegen einfaches Bearbeiten geschützt). Ein veränderter Client könnte das Item trotzdem zeigen; das Backend prüft fremden Besitz nicht.
- **Modell und Textur stecken in der JAR.** Wer die Datei auspackt, sieht Name und Aussehen.
- **Stärker wäre** eine Prüfung im Backend mit einer Liste erlaubter UUIDs, beim Einlösen und beim Weitergeben an andere Spieler. Das ist noch nicht eingebaut.

### Texturen aus einem Skin
Figuren aus einem Minecraft-Skin bekommen ihre Textur reproduzierbar aus der Skin-Datei im Projekt; die Anleitung steht im Kopf des Generators in `tools/`.

## Update 3.90.0: Fehler bei Freundes-Stats und Chat behoben

- **Stats in der Freundesliste:** Die Texte laufen nicht mehr in die Geschenk-Zeile. Das Feld war noch für fünf Besitz-Zeilen berechnet, inzwischen sind es neun.
- **Reihenfolge im Chat:** Eigene Nachrichten, die noch auf die Antwort des Backends warten, stehen jetzt dort, wo sie abgeschickt wurden. Eine später eintreffende Antwort des Freundes steht darunter. Nach der Bestätigung gilt die Reihenfolge und die Uhrzeit des Backends.
- **Vorschau in der Chat-Liste:** Emojis erscheinen dort als Bild statt als Kürzel wie `:creeper:`.

## Update 3.89.0: Neuer Anzeigename für ein exklusives Item

Ein exklusives Item trägt jetzt einen anderen Anzeigenamen. Die interne Item-Id bleibt gleich, bestehende Freischaltungen, Codes und die Anzeige bei anderen Spielern bleiben also gültig.

## Update 3.88.0: Exklusive Mounts per Code

Mounts können jetzt exklusiv sein: nur per Redeem-Code, nie im Goon Shop, nicht im Hourly Shop, nicht in der Wunschliste und ohne gesperrte Vorschau. Vor der Freischaltung zeigt die Oberfläche nichts davon. Nach dem Einlösen öffnet sich das Inventar mit dem vorausgewählten Item und einem kurzen Lichteffekt. Exklusive Mounts sind rein kosmetisch: Sie ändern weder Tempo noch Sprunghöhe, Flug, Hitbox oder Servermechanik und senden kein Paket an den Minecraft-Server. Schweben ist nur optisch.

### Einen eigenen Code einrichten
Das läuft über das vorhandene Code-System, im Projekt steht dafür kein Klartext. In `codes.json` landet nur ein Hash.
1. Im Projektordner ausführen, die Item-Id steht in `ShopCatalog` beziehungsweise bei dir:
   ```bash
   py -3 tools/backend/add_code.py 0 --item <item-id> --max-uses 1
   ```
2. Der ausgegebene Code erscheint nur dieses eine Mal. Er wird nicht gespeichert.
3. `tools/backend/codes.json` im Backend-Repo ersetzen und auf Render deployen.
4. Innerhalb von 7 Tagen im Goon Shop unter **Redeem code** einlösen. Die Freischaltung bleibt danach dauerhaft in `wallet.json`.

### Schutz, ehrlich
- **Der Code wird auf dem Server geprüft**, nicht im Client. Wer den Programmcode liest, findet ihn also nicht. `--max-uses 1` lässt nur ein Konto einlösen.
- **Der Besitz liegt danach im Client.** `wallet.json` ist gegen einfaches Bearbeiten geschützt, aber ein veränderter Client könnte das Mount trotzdem anzeigen. Das Backend prüft fremden Besitz nicht, es nimmt nur das Format der Id an.
- **Das Modell steckt in der JAR.** Wer die Datei auspackt, kann Name und Aussehen sehen.
- **Stärker wäre** eine Prüfung im Backend mit einer Liste erlaubter UUIDs, sowohl beim Einlösen als auch beim Anzeigen. Das ist noch nicht eingebaut.

### Texturen
Mit demselben Maler wie alle Mounts, Ausgabe auch als `build/signature_texture.png`:
```bash
javac -encoding UTF-8 -cp "build/classes/java/client;build/classes/java/main" -d build/tools tools/GenerateMounts.java tools/GenerateSignatureMount.java
java -cp "build/tools;build/classes/java/client;build/classes/java/main" GenerateSignatureMount
```

## Update 3.87.0: Chat-Befehle /msg und /r entfernt

Der Freunde-Chat hat keine eigenen Befehle mehr. Geschrieben wird im Chat-Tab und im Overlay. `/msg` und `/r` gehören damit wieder ganz dem Server: GoonClient fängt sie nicht mehr ab, und Nachrichten an Freunde gehen darüber nicht mehr in den Freunde-Chat.

## Update 3.86.0: Hüte, Accessoires und Flügel neu gestaltet

Alle 54 Items sind neu gebaut: 19 Hüte, 14 Flügel, 21 Accessoires. Ids, Namen, Preise, Seltenheiten, Besitz (`wallet.json`), Konfigurationen und Sync bleiben unverändert, das Protokoll auch. Neue Ids gibt es nicht. Zuordnung: Mechanik ist `circuit`, Kristall ist `ice`, Geist ist `shadow`, Brillen sind `glasses` und `monocle`, die Maske ist `bandana`, Helme sind `viking` und `cyberhelm`.

### Neue Gestaltung
- **Eigene Textur je Item** statt einer gemeinsamen weißen Fläche: 512 Pixel breit, 4 Texel pro Modell-Pixel. Jedes Teil bekommt fünf Töne aus seiner Farbe, Licht von oben links und ein Materialmuster: Stoff, Filz, Strick, Leder mit Naht, Metall mit Glanzkante, Gold, Edelstein, Kristall, Glas mit Reflex, Fell, Feder mit Kiel, Haut mit Adern, Schuppen, Knochen und mehr.
- **Formen statt Klötzchen**: Flache Teile bekommen über Transparenz einen Umriss, zum Beispiel Feder, Flamme, Zacke, Blatt, Stern oder Hautbahn. Teile können gedreht sein, runde Körper sind Achtecke.
- **Gelenke**: Federn, Quasten, Bänder und Ketten schwingen nach. Flügel haben je Seite Schulter, Arm, Hand und zwei Federreihen, jedes Segment läuft dem vorigen nach.
- **Flügelbewegung**: ruhiges Atmen im Stand, leichtes Auffächern beim Laufen, kräftiges Schlagen beim Sprinten und Springen, Anheben beim Fallen, Anlegen beim Schleichen und Schwimmen, mit weichen Übergängen.
- **Seltenheit**: Common schlicht, ab Epic immer Leuchtteile, Legendary mit den meisten Teilen und Effekten. Prism und Cosmic behalten ihr Farbspiel, aber deutlich ruhiger.
- **Leuchtteile** sind eigene Modellteile mit `entityTranslucentEmissive` und voller Helligkeit, keine zweite Textur. Sie pulsieren sanft und flackern nicht.
- **Effekte**: Federn, Funken, Glitzer oder Kristallstaub an einigen Flügeln und Accessoires, höchstens 8 je Item. Beim Sprinten werden es mehr. Abschaltbar.

### Konfliktregeln
- **Rucksack und Flügel**: Die Flügel rücken um 3,4 Pixel nach hinten.
- **Cape und Flügel**: Einstellung **With cape** bei den Flügeln. **Hide cape** (Standard) blendet das Cape aus, **Move wings back** rückt die Flügel 1,6 Pixel nach hinten. Sie schneiden sich dann beim Laufen trotzdem etwas, weil das Cape weit ausschwingt.
- **Elytra und Flügel**: Die Flügel werden ausgeblendet, die Elytra hat Vorrang.
- **Hoher Hut**: Das Namensschild rückt nur so weit hoch wie nötig, höchstens 0,45 Blöcke.
- Die Regeln gelten für jeden Spieler nach den Einstellungen des Betrachters.

### Vorschau und Einstellungen
- Große Vorschau in Shop und Inventar: mit der Maus drehen, **Reset view**, bei Flügeln Stand, Walk, Sprint, Jump, dazu **With my outfit** für Hut, Accessoire und Flügel zusammen. Seltenheitsrahmen, leichter Schein ab Epic.
- Hut: **Size**, **Effects**. Flügel: **Size**, **Flap strength**, **Particles**, **With cape**. Accessoire: **Effects**. **Size** und **Flap strength** gelten nur für die eigene Ansicht, andere Spieler sehen die Normalgröße. Ein Accessoire hat keine Größe, weil es sonst nicht mehr am Gesicht säße.
- "Goon Cosmetics" hat für diese Plätze keine eigene große Vorschau bekommen, sie liegt in Shop und Inventar.

### Technik und Leistung
- Daten in `ArtHats`, `ArtWings`, `ArtAccessories` mit dem Baukasten `ArtKit`. Neues Item: dort eine Methode ergänzen, im `ShopCatalog` eintragen, Skript laufen lassen.
- Jedes Gelenk ist ein einmal gebautes Modellteil, gezeichnet wird über die PoseStack. Im eigenen Code entsteht pro Bild nichts Neues. Grenzen je Item: 90 Teile, 24 Gelenke, im Test geprüft.
- Entfernung: Ab 32 Blöcken fallen Nachschwingen, Hand und Teilchen weg, ab 64 Blöcken steht das Modell still.

### Texturen neu erzeugen
Nach einem Build, im Projektordner:
```bash
java -cp "build/classes/java/client;build/classes/java/main" tools/GenerateCosmeticAccessories.java
```
Das schreibt `textures/accessory/items/<id>.png`. `tools/AccessoryArtTest.java` meldet, wenn eine Textur nicht mehr zu den Daten passt.

### Vorher und nachher
Vorher nutzten alle Items dieselbe weiße Textur ohne Gelenke.

| Item | Platz | Seltenheit | Teile vorher | Teile nachher | Gelenke | Textur nachher |
|---|---|---|---|---|---|---|
| cap | Hat | Common | 3 | 14 | 1 | 512x96 |
| beanie | Hat | Common | 3 | 20 | 1 | 512x192 |
| chef | Hat | Uncommon | 3 | 24 | 1 | 512x224 |
| tophat | Hat | Uncommon | 3 | 18 | 1 | 512x288 |
| cowboy | Hat | Uncommon | 6 | 16 | 1 | 512x224 |
| wizard | Hat | Rare | 9 | 29 | 2 | 512x256 |
| crown | Hat | Rare | 13 | 45 | 1 | 512x192 |
| viking | Hat | Rare | 12 | 46 | 1 | 512x192 |
| flamecrown | Hat | Epic | 10 | 49 | 9 | 512x192 |
| cosmic | Hat | Legendary | 9 | 42 | 2 | 512x320 |
| headband | Hat | Common | 4 | 9 | 2 | 512x96 |
| partyhat | Hat | Uncommon | 6 | 45 | 2 | 512x160 |
| santa | Hat | Uncommon | 7 | 20 | 2 | 512x256 |
| witch | Hat | Rare | 8 | 29 | 2 | 512x320 |
| propeller | Hat | Epic | 7 | 21 | 2 | 512x128 |
| starcrown | Hat | Legendary | 11 | 50 | 2 | 512x160 |
| reaperhood | Hat | Rare | 10 | 18 | 1 | 512x192 |
| jackolantern | Hat | Epic | 18 | 23 | 1 | 512x160 |
| cyberhelm | Hat | Epic | 10 | 23 | 2 | 512x192 |
| paper | Wings | Common | 4 | 10 | 11 | 512x64 |
| bat | Wings | Uncommon | 14 | 26 | 11 | 512x192 |
| fairy | Wings | Rare | 8 | 12 | 11 | 512x64 |
| angel | Wings | Rare | 12 | 50 | 11 | 512x224 |
| demon | Wings | Epic | 16 | 42 | 11 | 512x288 |
| dragon | Wings | Epic | 19 | 50 | 11 | 512x320 |
| phoenix | Wings | Legendary | 14 | 66 | 11 | 512x288 |
| prism | Wings | Legendary | 16 | 71 | 11 | 512x288 |
| butterfly | Wings | Uncommon | 18 | 5 | 11 | 512x96 |
| shadow | Wings | Rare | 16 | 36 | 11 | 512x224 |
| ice | Wings | Epic | 14 | 40 | 11 | 512x192 |
| skeleton | Wings | Rare | 22 | 40 | 11 | 512x128 |
| vampire | Wings | Epic | 20 | 42 | 11 | 512x288 |
| circuit | Wings | Epic | 26 | 46 | 11 | 512x192 |
| glasses | Accessory | Common | 6 | 14 | 1 | 512x32 |
| headphones | Accessory | Common | 7 | 12 | 1 | 512x64 |
| catears | Accessory | Uncommon | 8 | 9 | 1 | 512x96 |
| scarf | Accessory | Uncommon | 5 | 12 | 2 | 512x64 |
| backpack | Accessory | Uncommon | 8 | 20 | 1 | 512x96 |
| horns | Accessory | Rare | 6 | 18 | 1 | 512x32 |
| visor | Accessory | Epic | 5 | 12 | 1 | 512x64 |
| halo | Accessory | Epic | 4 | 10 | 2 | 512x64 |
| crystals | Accessory | Legendary | 6 | 24 | 2 | 512x32 |
| mustache | Accessory | Common | 5 | 5 | 1 | 512x32 |
| bowtie | Accessory | Common | 5 | 6 | 1 | 512x32 |
| monocle | Accessory | Uncommon | 6 | 9 | 2 | 512x32 |
| bandana | Accessory | Uncommon | 9 | 14 | 2 | 512x96 |
| flowercrown | Accessory | Rare | 10 | 30 | 1 | 512x128 |
| wisps | Accessory | Epic | 4 | 24 | 2 | 512x32 |
| aura | Accessory | Legendary | 8 | 17 | 2 | 512x96 |
| fangs | Accessory | Common | 5 | 5 | 1 | 512x32 |
| spider | Accessory | Uncommon | 21 | 30 | 9 | 512x64 |
| ghosts | Accessory | Legendary | 12 | 45 | 2 | 512x64 |
| cubes | Accessory | Epic | 8 | 28 | 2 | 512x64 |
| hackerorbit | Accessory | Exclusive | 75 | 75 | 2 | 512x64 |

### Grenzen
- Alle Teile sind Quader und flache Karten. Von der Seite gesehen verschwinden flache Karten fast, zum Beispiel die Zacken der Kronen (dafür gibt es Stege) und Federspitzen.
- Getestet wurde mit einem Testskin. Skins mit ungewöhnlich sitzendem Gesicht passen zu Schnurrbart und Reißzähnen nicht immer, sie liegen an der üblichen Stelle.
- Rüstung: Ein Helm schneidet mit Hüten und anderem am Kopf, wie schon zuvor.

### Getestet
- `tools/AccessoryArtTest.java`: Teile-Hierarchie, UV-Bereiche ohne Überlappung, Leuchtmasken, Drehpunkte, Gelenkwinkel, NaN, Konfliktregeln, Teilchen-Grenzen, Sitz, Ids, Preise, Wallet.
- Im echten Spiel: Prüfbogen für jedes Item (vorne, Seite, hinten, schräg, bei Flügeln Walk, Sprint, Jump), außerdem echter Spieler in der Welt mit Hut, Rucksack und Flügeln im Stand, beim Sprinten und Schleichen.

**Nicht getestet**: andere Spieler auf einem echten Server, Emotes und Mounts zusammen mit den neuen Hüten, Fallen und Schwimmen im Spiel (nur in der Logik), die FPS-Wirkung mit vielen Spielern, Maus-Ziehen in der Vorschau von Hand, Elytra, "Move wings back" und die Höhe des Namensschilds im Bild (nur in der Logik). Neue Mixins gibt es nicht: Cape und Namensschild laufen über den vorhandenen Eingriff mit `require = 0`.

## Update 3.85.0: Weather & Time Changer

Neues Modul in der Kategorie **Render**: Tageszeit und Wetter nur in der eigenen Ansicht. Es startet im Vanilla-Verhalten und verändert nichts, solange nichts eingestellt ist. Zusätzlich gibt es das HUD-Modul **Weather & Time** (Uhrzeit und Wetter, einzeln abschaltbar).

### Einstellungen
- **Zeit**: Vanilla, Fixed (Regler in Ticks mit Uhrzeit, Schnellwahl Morning, Noon, Evening, Midnight), Real time (folgt deiner Uhr, mit Verschiebung), Cycle (0,1x bis 10x, mit Pause). Mondphase Auto oder eine von acht.
- **Wetter**: Vanilla, Clear, Rain, Thunder, Snow (auch in warmen Biomen, nur optisch), Fog. Dazu Intensity, Lightning (Off, Rare, Normal), Dim lightning flash, Thunder sound, Fog strength.
- **Atmosphäre**: Clouds, Star brightness, Sunset glow, Sky brightness, Transition (1 bis 3 s).
- **Fairness**: Keep game brightness. **Sky**: Use sky recommendation.
- **Presets**: Golden Hour, Blue Hour, Eternal Night, Dawn, Storm, Snowy Evening, Foggy Morning und eigene (Name eingeben, Save, Delete). Tasten für nächstes Preset, Zeit +/-, nächstes Wetter (ab Werk nicht belegt).
- **Vorschau** ganz oben: zeigt Zeit, Wetter und den ausgerüsteten Himmel live. Der Regler darunter probiert nur Zeiten aus und verändert die Welt nicht, "Live" geht zurück.
- **Diagnose** ganz unten: Time hook, Weather hook, Sky link.

### Zusammenspiel mit den Skys
`com.goonclient.environment.EnvironmentState` (reines Java) ist die eine Quelle für Tageszeit, Mondphase, Regen, Gewitter, Schnee, Nebel, Wolken und Sterne. Sie kombiniert Server, Modul und Übergang.
- Minecraft 1.21.11 berechnet Sonne, Mond, Himmelsfarben, Wolken- und Nebelfarbe über "Environment Attributes". Nur diese sichtbaren Attribute bekommen in der Client-Welt eine andere Zeit- und Wetterquelle. Davon leben der normale Himmel und die Skys gleichermaßen, sie können also nicht auseinanderlaufen. Die Skys bekommen Wetter und Atmosphäre zusätzlich über `SkyMath.atmosphere`, Horizont und Fernnebel ziehen mit.
- Einen neuen Sky bindet man mit `.recommend(tick, wetter, stärke, "stimmung")` in `SkyCatalog` an. Ohne Eintrag gilt die Tageszeit seiner Vorschau bei klarem Wetter.

### Was unberührt bleibt
Es werden keine Pakete gesendet oder verändert. Weltzeit, Schlafen, Spawns, Pflanzen, Blitzschäden und echtes Wetter bleiben. Abfragen wie "steht der Spieler im Regen" bleiben echt, deshalb funktioniert zum Beispiel der Dreizack weiter nach dem echten Wetter. Nether und End bleiben unverändert. Blitze des Moduls entstehen nur auf deinem Client, weit entfernt und ohne Wirkung. Echte Blitze bleiben sichtbar, auch im Modus Clear.

### Fairness und Verantwortung
"Keep game brightness" ist ab Werk an: Die Welthelligkeit folgt weiter dem Server, nur Himmel und Wetter sehen anders aus. Ist sie aus, ändert sich auch die Helligkeit der Welt, und das Menü warnt. **Manche Server verbieten Zeit- oder Wetteränderungen auf dem Client, dafür bist du selbst verantwortlich.** Auch "klares Wetter" ohne die Helligkeit kann als Sichtvorteil gelten. Blitze sind ab Werk gedämpft, abschaltbar, kommen nie schnell hintereinander und klingen weich ab.

### Grenzen
- Mit "Keep game brightness" liegt am Boden das Licht der echten Zeit: Mitternachtshimmel über hellem Gras, oder klarer Himmel über dunklem Gras bei echtem Gewitter. Das ist gewollt.
- Regen und vor allem Gewitter machen die Skys sehr dunkel, ihre Eigenheiten sind dann kaum noch zu sehen.
- Schnee ist nur Schneefall und Himmel, am Boden liegt kein Schnee. Die Flocken sind die von Minecraft und wirken bei hoher Intensität dicht.
- Wolken an/aus schaltet die Wolken von Minecraft hart um, die der Skys blenden weich.
- Die Mondphase der Skys nimmt nur bei fester Wahl eine Form an; Auto zeigt dort wie bisher den vollen Mond.

### Getestet
- `tools/EnvironmentLogicTest.java`: stetige Übergänge, kürzester Weg über Mitternacht, Echtzeit, Zyklus, Wertebereiche und NaN, Kombination aus Server, Modul und Übergang, Presets, alte Konfigurationen, Empfehlungen, Dimensionen, Blitzabstände, alle Skys in allen Zeiten und Wetterlagen auf gültige Werte.
- Im echten Spiel per Gametest: Hooks aktiv, Modul aus und auf Vanilla identisch, feste Zeit ändert Sonne, aber weder Weltzeit noch Welthelligkeit, ohne "Keep game brightness" auch die Helligkeit, echtes Gewitter bei Modus Clear, Nether unverändert, Kontaktbogen (Vanilla und 5 Skys, 4 Zeiten, 4 Wetterlagen), Nebel, Mondphasen, Menü und HUD.

**Nicht getestet**: echte Server mit Plugins, Shader und andere Mods, echtes Gelände und Höhlen (nur Superflat und ein Blick in den Nether), Tastendruck und Ziehen der Regler von Hand, Geräusche (im Test nicht hörbar), Free Look und Motion Blur zusammen mit dem Modul. Der eigene Blitz wurde als Objekt und Lichtblitz gemessen, im Bild aber nicht gesehen.

### Schnell im Spiel prüfen
In einer Testwelt mit Cheats: `/time set 6000` und `/weather clear`, Modul an, Time mode **Fixed**, 18000. Der Himmel wird Nacht, `/time query daytime` zeigt weiter die echte Zeit. Dann `/weather thunder` mit Weather mode **Clear**: Der Himmel bleibt klar. Unten im Modul muss bei Time hook und Weather hook "yes" stehen.

## Update 3.84.0: Coins auch AFK verdienen

Goon Coins und Event-Coins laufen jetzt in jeder Welt durch, auch ohne Eingabe und mit dem Fenster im Hintergrund. Die Anzeige "AFK: paused" ist weg. Keine Coins gibt es nur außerhalb einer Welt und wenn das Spiel pausiert ist. Im Einzelspieler pausiert es beim Wechsel in ein anderes Fenster, wenn die Minecraft-Option "Pause on Lost Focus" an ist.

Die 3 Minuten AFK-Erkennung (`ActivityTracker`) gilt nur noch für Missionsminuten und Battle-Pass-XP, die weiter aktives Spielen brauchen. Die Mission "Coins verdienen" zählt AFK-Coins dagegen mit, weil sie an den Coins hängt.

Ältere Abschnitte dieser README, die "AFK zählt nicht" sagen, beschreiben den Stand davor.

## Backend: Freunde, Chats und Blocklisten bleiben erhalten

Render Free hat keine dauerhafte Festplatte: Bei jedem Deploy und jedem Aufwachen startet das Backend mit leerer Datenbank. Deshalb kann `server.py` die Datenbank jetzt automatisch in ein **privates GitHub-Repo** sichern und beim Start zurückholen. Das kostet nichts und braucht keine neuen Pakete. Der Client ist unverändert, die Version bleibt 3.83.0.

**Einrichten** (Umgebungsvariablen auf Render):
- `GOON_BACKUP_REPO`: `name/repo` eines privaten Repos mit mindestens einer Datei
- `GOON_BACKUP_TOKEN`: ein Fine-grained Token, nur für dieses Repo, mit der Berechtigung Contents: Read and write
- optional `GOON_BACKUP_SECONDS` (Standard 120)

**Was passiert**
- Gesichert wird die ganze Datenbank: Freunde, Chats, Blocklisten, Meldungen, Cosmetics, Stats und eingelöste Codes. Die Dateien liegen als Release `goon-backup` im Repo.
- Alle 2 Minuten, wenn sich etwas geändert hat, und beim Beenden durch den Hoster. Es bleiben die neuesten 3 Stände und der neueste Stand der letzten 3 Tage mit Sicherungen.
- `https://DEIN-BACKEND/v1/health` zeigt den Zustand: `ok`, `failing` (Hochladen klappt gerade nicht), `blocked` (Token oder Repo falsch, oder das Repo ist öffentlich), `off` (nicht eingerichtet).

**Schutz der Sicherung**
- Ist GitHub beim Start nicht erreichbar, beendet sich der Server und wird vom Hoster neu gestartet. Er läuft nicht leer los.
- Bei falschem Token oder öffentlichem Repo läuft die Website weiter, aber es wird nichts hochgeladen. Spieler sehen dann leere Listen, bis das behoben und neu gestartet ist; was in dieser Zeit passiert, wird verworfen.
- Eine beschädigte Sicherung wird erkannt, dann kommt die davor.

**Grenzen**
- Stürzt der Server ab, fehlen höchstens die letzten 2 Minuten. Render startet beim Deploy die neue Instanz, bevor die alte endet: Was in diesen Sekunden bei der alten ankommt, kann ebenfalls fehlen.
- Der Token läuft zum gewählten Datum ab, dann steht `/v1/health` auf `blocked` beziehungsweise `failing`. Rechtzeitig erneuern.
- Chats liegen unverschlüsselt in der Sicherung. Wer Zugriff auf das private Repo hat, also du und GitHub, könnte sie lesen. Gelöschte und abgelaufene Nachrichten können in alten Sicherungen noch bis zu 3 Tage stehen, also über die 7 Tage hinaus.
- Bei mehreren Instanzen gleichzeitig funktioniert das nicht, eine reicht hier aber.

**Getestet** mit `tools/backend/test_backup.py`: echtes `server.py` gegen einen Nachbau der GitHub-Schnittstelle (`mock_github.py`), mit Neustarts auf leerem Ordner, Absturz, falschem Token, GitHub-Störung, öffentlichem Repo und beschädigter Sicherung. **Nicht getestet**: gegen das echte GitHub und auf dem echten Render, dafür braucht es dein Token.

## Update 3.83.0: Freunde-Chat (live) mit Emojis und Stickern

Neuer Tab **Chat**: privater 1:1-Chat mit bestätigten Freunden, auf jedem Server und im Hauptmenü, über das GoonClient-Backend.

### Benutzung
- **Freunde**: Chatten geht nur mit Spielern, die eine Anfrage angenommen haben. Lokale Freunde ohne Verbindung stehen im Chat-Tab unter "Not connected yet" mit dem Knopf **Request**. Offene Anfragen lassen sich dort auch annehmen. Höchstens 100 verbundene Freunde (`MAX_FRIENDS`).
- **Chat-Tab**: links Freunde mit Status und Ungelesen-Zähler, rechts der Verlauf. Enter sendet. Nach oben scrollen lädt ältere Nachrichten. Fährt man über eine Nachricht: **x** löscht die eigene für beide, **!** meldet die fremde (jeweils zweimal klicken). Oben: Mute, Clear (nur hier löschen), Report, Block.
- **Overlay im Spiel**: Taste **O** (änderbar) öffnet den kleinen Chat. Esc schließt. Das Spiel läuft weiter.
- **Befehle**: Die Chat-Befehle `/msg` und `/r` wurden in 3.87.0 wieder entfernt.
- **Emojis**: `:gg:`, `:goon:`, `:coin:`, `:totem:`, `:creeper:`, `:sus:` und 74 weitere. Beim Tippen von `:` erscheint eine Vervollständigung (Tab oder Enter wählt). Standard-Emojis werden beim Senden zu eigenen, was keine Entsprechung hat, wird zu `?`. Unbekannte Kürzel bleiben Text.
- **Sticker**: Knopf neben dem Eingabefeld: Reiter pro Paket, Last (zuletzt benutzt), Favs (Stern), Suche. Übertragen wird nur die Id (`goonclassic.gg`). Unbekannte Ids erscheinen als `[Sticker]`.
- **Pakete**: Goon Classic (14) ist frei. Minecraft Vibes (10, 120 Coins), Memes (11, 300) und Animated (9, 700) kommen als Kategorie "Stickers" in die normale Goon-Shop-Rotation. Empfänger sehen immer alle Sticker. Der Besitz wird nur im Client geprüft; das Backend prüft nur das Format, ein veränderter Client könnte also fremde Pakete senden.
- **Einstellungen** (Knopf "Chat settings"): Banner, Sound, Do not disturb, Online-Status zeigen, Wortfilter mit eigenen Wörtern, Chat-Taste, Größe und Position des Overlays, Sticker-Animationen. Dort steht auch die Blockliste. Alte Konfigurationen laden unverändert.
- Die Bedientexte sind Englisch wie das ganze Menü, deshalb heißt "Langsamer, bitte" im Spiel "Slow down, please."

### Grenzen
300 Zeichen pro Nachricht, keine Steuerzeichen und kein §. Links bleiben reiner Text und werden nie geladen. 20 Nachrichten pro Minute und 5 pro 5 Sekunden je Konto (Client und Backend), 20 Freundschaftsanfragen pro Tag. Das Backend hält pro Unterhaltung höchstens 200 Nachrichten und löscht sie nach 7 Tagen. Der Client hält je Unterhaltung höchstens 200 im Speicher und speichert den Verlauf nicht auf der Platte, er kommt beim Öffnen vom Backend. Keine Gruppen, öffentlichen Räume, Dateien, Standorte oder Link-Vorschauen.

### Sicherheit und Datenschutz
- Der Weg zum Backend läuft über HTTPS. **Die Nachrichten sind nicht Ende-zu-Ende-verschlüsselt: Wer das Backend betreibt, kann sie lesen.** Gespeichert werden nur UUID-Paare, Text oder Sticker-Id, Zeit und Status.
- Der Absender kommt immer aus dem Anmelde-Token. Nachrichten lesen und schreiben können nur die beiden Beteiligten.
- **Blockieren**: Der Blockierte kann keine Anfragen und Nachrichten mehr schicken und erfährt es nicht direkt. Für ihn sieht es aus, als wäre die Freundschaft beendet.
- **Melden** speichert die letzten 20 Nachrichten der Unterhaltung für 90 Tage, also länger als die normalen 7 Tage.
- Der Wortfilter wirkt beim Empfänger und ist einfach gehalten: Er erkennt nur ganze Wörter, Umschreibungen rutschen durch.

### Meldungen ansehen
Auf dem Backend die Umgebungsvariable `GOON_ADMIN_TOKEN` auf ein langes Geheimnis setzen, dann:
```bash
curl -H "Authorization: Bearer DEIN_TOKEN" https://DEIN-BACKEND/v1/admin/reports
```
Ohne gesetztes Token gibt es diese Adresse nicht (404).

### Backend und Render
Der Live-Kanal ist Long-Polling mit der Python-Standardbibliothek: **keine neuen Pakete, keine requirements.txt, kein neuer Startbefehl**. Es reicht die neue `server.py`. Sie bringt neue Tabellen mit und legt sie selbst an; die alten Endpunkte bleiben gleich, ältere Clients laufen weiter.
- Render Free legt den Dienst nach etwa 15 Minuten ohne Anfragen schlafen, das Aufwachen dauert bis zu einer Minute. Der Client verbindet dann von selbst neu, Nachrichten kommen in dieser Zeit verzögert an. Solange jemand online ist, hält der Chat den Dienst wach, das verbraucht freie Stunden.
- Das Dateisystem von Render Free ist nach jedem Neustart und Deploy leer: **Ohne Persistent Disk sind Nachrichten, Blocklisten und Freundschaften dann weg.** Freundschaften fragt der Client still neu an, dabei kann das Limit von 20 Anfragen pro Tag bremsen. Empfehlung: eine Persistent Disk (bezahlte Instanz) und `--db` auf einen Pfad darauf. Alle Speicherzugriffe liegen in der Klasse `Store` in `server.py`, ein Wechsel auf eine externe Datenbank betrifft nur sie.
- `--chat-ttl` oder `GOON_CHAT_TTL` ändert die Haltezeit (Sekunden).

### Sticker neu erzeugen
Alle Bilder malt `tools/GenerateStickers.java`, nichts wird geladen. Nach einem Build im Projektordner:
```bash
java -cp build/classes/java/client tools/GenerateStickers.java
```
Das schreibt `textures/chat/emoji.png`, `textures/chat/stickers/*.png` und die Übersicht `build/chat_contact_sheet.png`.

### Wie es gebaut ist
Reine Logik ohne Minecraft in `com.goonclient.chat` (Regeln, Emoji-Parser, Zustellzustand, Rate-Limit, Verlauf, Zähler, API), Spiel-Anbindung in `com.goonclient.chat.game`. Das Netz läuft nur auf Hintergrund-Threads, bei Fehlern mit wachsendem Abstand bis 30 s und etwas Zufall. Neue Mixins gibt es nicht.

### Getestet
- `tools/ChatLogicTest.java`: Regeln, Emoji-Parser mit Randfällen, Sticker-Ids und Bilddateien, Rate-Limit, Zustand, Verlauf, Zähler.
- `tools/backend/test_chat.py` gegen das echte Backend: Freunde, Anfragelogik (doppelt, Gegenanfrage, Block), live senden, offline, Lesebestätigung, Block, Entfernen, Rate-Limit, ungültige Ids und lange Texte, fremde Konten, Löschen nach verkürzter Haltezeit, Meldung.
- `tools/BackendIntegrationTest.java`: der Java-Client gegen das echte Backend.
- Im echten Spiel per Gametest mit eingespielten Daten: Chat-Tab, Emoji- und Sticker-Auswahl, Vervollständigung, Einstellungen, Overlay, Banner, `/msg` und `/r`.

**Nicht getestet**: zwei echte Spieler über das echte Backend auf Render. Im Gametest ist keine Anmeldung möglich (Testkonto), die Verbindung Spiel zu Backend lief dort also nie. Beide Hälften sind einzeln geprüft, aber nicht zusammen im Spiel. Auch `/msg` auf einem Server mit eigenen Plugins und die Tastenbedienung im Overlay wurden nicht durchgespielt.

## Update 3.82.0: Codes laufen nach 7 Tagen ab

- **Neue Regel:** Jeder Redeem-Code gilt nur noch 7 Tage. `add_code.py` setzt den letzten gültigen Tag automatisch auf heute + 7 (UTC). Mit `--expires` geht es nur kürzer, nicht länger.
- **Bestehende Codes:** Die Codes in `codes.json` gelten jetzt bis einschließlich 09.11.2026, auch die eingebauten Codes im Client. Nur die beiden Halloween-Codes enden wie geplant schon am 06.11.2026, zusammen mit dem Event.
- **Sicherung im Backend:** Ein Code ohne gültiges Datum oder mit einem Datum mehr als 7 Tage in der Zukunft gilt als abgelaufen, auch wenn `codes.json` von Hand geändert wurde. Solche Codes erscheinen auch nicht auf der Website.
- **Was bleibt:** Bereits eingelöste Coins und Items behalten die Spieler. Abgelaufene Codes verschwinden von der Website.
- **Grenze:** Clients bis 3.81.0 kennen das Ablaufdatum ihrer eingebauten Codes (`launch100`, `bonus3000`) nicht. Ohne Online-Anmeldung lassen sie sich dort weiter lokal einlösen. Online lehnt das Backend sie ab.

## Update 3.81.0: Fahrzeuge und Fantasie-Gefährte

15 neue Mounts, die keine Tiere sind. Sie nutzen dieselbe Technik wie die Reittiere und kommen in die normale stündliche Rotation des Goon Shops. Kauf, Besitz und `wallet.json` funktionieren wie bei allen Items, alte Wallets laden weiter.

**Fairness: Kosmetisch, ohne Spielvorteil.** Kein Tempo, kein Sprung, kein Fliegen, gleiche Hitbox, kein eigenes Server-Paket. Schwebende Mounts schweben nur optisch, der Spieler selbst fliegt nicht und bleibt, wo er ist.

| Mount | Id | Seltenheit | Preis |
|---|---|---|---|
| Skateboard | `mount.skateboard` | Common | 30 |
| City Bike | `mount.bicycle` | Common | 40 |
| Wooden Sled | `mount.sled` | Common | 50 |
| Hoverboard | `mount.hoverboard` | Uncommon | 90 |
| Flying Carpet | `mount.carpet` | Uncommon | 110 |
| Magic Broom | `mount.broom` | Uncommon | 130 |
| Motorcycle | `mount.motorcycle` | Rare | 220 |
| Retro Roadster | `mount.car` | Rare | 300 |
| Cloud Pillow | `mount.cloud_pillow` | Rare | 380 |
| Hover Train | `mount.hover_train` | Epic | 550 |
| UFO | `mount.ufo` | Epic | 750 |
| Walker Mech | `mount.mech` | Epic | 950 |
| Starship | `mount.spaceship` | Legendary | 1600 |
| Sky Galleon | `mount.airship` | Legendary | 2200 |
| Sky Throne | `mount.sky_throne` | Legendary | 2900 |

- **Bewegung:** Räder drehen sich passend zum Tempo. Fahrzeuge neigen sich in Kurven, nicken beim Beschleunigen und federn beim Landen. Schwebende Mounts halten einen geglätteten Bodenabstand und sinken beim Schleichen etwas ab. Fransen, Segel, Seile, Antennen und Kupplungen schwingen nach.
- **Hover Train:** Zwei Wagen folgen der Spur des Zugkopfs. In der Vorschau fährt er eine Kurve. Dreht sich der Spieler im Stand, bleiben die Wagen stehen und knicken gegenüber dem Kopf ab.
- **Reiter:** Eigene Sitzposen je Mount: stehen auf dem Brett, sitzen im Sattel, im Cockpit oder im Schneidersitz. Auf dem Fahrrad treten die Beine mit. Emotes laufen weich über die Reitpose.
- **Leuchten und Effekte:** Scheinwerfer, Neon, Ringlichter und Triebwerke pulsieren sanft. Eigene Partikel je Mount, zum Beispiel Bremsfunken, Auspuffrauch, Schnee, Sternenstaub, Staub im Traktorstrahl und Plasma-Spur.
- **Neue Einstellungen:** Lights, Trail, Sound und Sound volume, zusätzlich zu Größe, Animation, Effekten, Sichtbarkeit und Ich-Ansicht. Sie gelten für das eigene Mount, bei anderen Spielern sind Lichter und Spur immer an.
- **Sound:** Standardmäßig aus. Es sind leise, gelegentliche Minecraft-Geräusche, kein durchgehender Motor. Sie richten sich auch nach dem Hauptschalter für GoonClient-Sounds, und Mounts anderer Spieler sind viel leiser und nur bis 16 Blöcke zu hören.
- **Vorschau:** Auf der großen Bühne heißen die Zustände Idle, Drive, Sprint und Jump.
- **Leistung:** Höchstens 60 Teile und 200 Quader je Mount, das größte hat zurzeit 61 Quader. Es gelten dieselben Grenzen wie bei den Reittieren: 24 Mounts gleichzeitig, 16 Partikel pro Sekunde je Mount, ab 32 Blöcken weniger Effekte, ab 64 nur noch das Modell.
- **Sync:** Die neuen Ids laufen über das vorhandene Feld `mount`, das Backend führt keine Liste. `tools/backend/server.py` hat sich seit 3.79.0 nicht geändert. Unbekannte Ids werden still ignoriert, fremder Besitz lässt sich nicht prüfen.

**Texturen neu erzeugen** (nach dem Bauen, aus dem Projektordner):

```bash
javac -encoding UTF-8 -cp build/classes/java/client -d build/tools tools/GenerateMounts.java tools/GenerateVehicleMounts.java
```

```bash
java -cp "build/tools;build/classes/java/client" GenerateVehicleMounts
```

Der Kontaktbogen liegt danach in `build/vehicle_textures.png`.

**Grenzen**

- Ein Motorgeräusch als durchgehende Schleife gibt es nicht, und die Sounds sind nur technisch eingebaut, nicht angehört.
- Die Wagen des Zugs weichen Wänden nicht aus und können durch Blöcke fahren. Auch große Modelle wie Galleone und Raumschiff ragen an Wänden in den Block.
- Ein Namensschild für das Mount gibt es weiterhin nicht.
- Räder im Wasser bleiben optisch an der Oberfläche, eine eigene Boot-Variante gibt es nicht.

## Update 3.80.0: Reittiere komplett neu gestaltet

IDs, Preise, Besitz, Sync und Einstellungen bleiben gleich, alte Wallets und Konfigurationen laden weiter. Geändert haben sich Modelle, Texturen, Sitzpose, Effekte und die Vorschau. Ein Reittier ist weiterhin rein kosmetisch.

- **Modelle:** Hals in 3 Segmenten, Brust, Rumpf und Kruppe getrennt, Beine mit Oberschenkel, Knie, Fessel und Huf oder Pfote, Schweif in bis zu 5 Segmenten, Mähne in Strähnen, Unterkiefer, Nüstern, Sattel mit Gurt und teils Steigbügeln. Höchstens 60 Teile und 200 Quader je Reittier, das größte hat zurzeit 128 Quader (Drache). Mit Test abgesichert.
- **Proportionen:** Die Rückenhöhe liegt bei 1,1 bis 1,5 Blöcken. Sitzhöhe und Reitpose gelten je Reittier: Die Hüfte rückt nach außen, die Beine liegen links und rechts am Körper.
- **Texturen:** `tools/GenerateMounts.java` malt fünf Grundtöne plus Zwischenstufen mit Licht von oben links, dazu Fellstriche, Schuppenreihen, Federn, Rosetten, Rinde, Moos, Risse und Nähte. Kein Zufallsrauschen, gleiche Eingabe ergibt gleiche Bilder.
- **Leuchtteile:** Eigene Maske `mount_*_e.png`, gezeichnet mit `entityTranslucentEmissive`. Sie pulsieren sanft und leuchten auch nachts.
- **Eigene Effekte:** Staub und Gras nur im Galopp, Schneeflocken (Eisbär), Seelenfunken (Skelettpferd), Rauch und Funken am Maul sowie Flügelwind (Drache), Funken, Glut und Lava-Tropfen (Magma), Blätter und Pollen (Hirsch), Glut und Flammenfedern (Phoenix), Wolkenfetzen und Sternenstaub (Wal), Sternenstaub und Regenbogenspur (Einhorn). Der braune Sprint-Staub von Minecraft fällt beim Reiten weg.
- **Bewegung:** Schweif, Mähne, Zügel, Quasten, Geweih, Haube und Flügelfinger schwingen verzögert nach und reagieren auf Tempo, Kurven und Federn. Sprung mit Absprung, Flugphase und Landung, Hufe rollen ab, der Reiter verlagert sein Gewicht.
- **Boden:** Weicher Schatten, ab Rare bei einigen Reittieren ein Lichtkreis in der Farbe des Tiers, bei Legendary am stärksten.
- **Vorschau:** Große Bühne in Shop und Inventar mit Seltenheitsrahmen, Glow bei Epic und Legendary, Effekten als Lichtpunkten, Gangarten und Drehung per Ziehen oder Regler.
- **Leistung und Grenzen:** Höchstens 16 Partikel pro Sekunde je Reittier und 90 insgesamt, Partikel laufen über Minecrafts eigenes Partikelsystem. Ab 32 Blöcken gibt es weniger Effekte und keinen Lichtkreis, ab 64 nur noch das Modell, ab 128 nichts mehr. Höchstens 24 Reittiere gleichzeitig. Weil jedes Teil einzeln gezeichnet wird, kostet ein Reittier mehr als früher; gemessen habe ich das noch nicht.

**Texturen neu erzeugen** (nach dem Bauen, aus dem Projektordner):

```bash
javac -encoding UTF-8 -cp build/classes/java/client -d build/tools tools/GenerateMounts.java
```

```bash
java -cp "build/tools;build/classes/java/client" GenerateMounts
```

Der Kontaktbogen liegt danach in `build/mount_textures.png`.

**Bekannte Schwächen**

- Bei Seitenansicht verdecken die Arme des Reiters teils Hals und Kopf kleiner Tiere.
- Die Figuren bleiben aus Quadern gebaut, Rundungen sind gestuft. Flügel und Flossen wirken von der Kante aus dünn.
- Die Partikel der Vorschau sind einfache Lichtpunkte, im Menü gibt es keine echten Weltpartikel.
- Die Grenzen aus 3.79.0 zu Wänden, Cape und Größe für andere Spieler gelten weiter. Lange Tiere ragen an Wänden eher in den Block.

## Update 3.79.0: Reittiere (Mounts)

Neue Item-Art **Mount**: Du sitzt sichtbar im Sattel, das Reittier läuft unter dir mit. Mounts kommen wie alle anderen Items in die normale stündliche Rotation des Goon Shops, es gibt keinen eigenen Shop-Tab. Im Inventar haben sie einen eigenen Chip "Mounts".

**Fairness: Kosmetisch, ohne Spielvorteil.** Kein Tempo, kein Sprung, kein Fliegen, gleiche Hitbox, gleiche Reichweite, kein Server-Paket für die Bewegung. Gezeichnet wird nur anders: Der Spieler wird beim Zeichnen angehoben, seine echte Position ändert sich nie. Fliegende Reittiere schweben nur optisch.

| Reittier | Id | Seltenheit | Preis |
|---|---|---|---|
| Pony | `mount.pony` | Common | 40 |
| Donkey (Esel) | `mount.donkey` | Common | 50 |
| Saddled Pig (Schwein mit Sattel) | `mount.pig` | Common | 60 |
| White Horse (mit Zaumzeug) | `mount.horse_white` | Uncommon | 100 |
| Great Wolf | `mount.wolf` | Uncommon | 120 |
| Carpet Llama (Lama mit Decke) | `mount.llama` | Uncommon | 150 |
| Skeleton Horse (leuchtende Augen) | `mount.skeleton_horse` | Rare | 240 |
| Polar Bear | `mount.polar_bear` | Rare | 320 |
| Ocelot Panther | `mount.panther` | Rare | 400 |
| Dragon Whelp (mit Flügeln) | `mount.dragon` | Epic | 600 |
| Magma Cube (leuchtet, Funken) | `mount.magma` | Epic | 800 |
| Root Stag (Geweih, Moos, Blüten) | `mount.root_stag` | Epic | 1000 |
| Phoenix (schwebt, Glut) | `mount.phoenix` | Legendary | 2000 |
| Cloud Whale (schwebt, Wellen) | `mount.cloud_whale` | Legendary | 2400 |
| Rainbow Unicorn (Sternenstaub) | `mount.unicorn` | Legendary | 3000 |

"No Mount" (`mount.none`) gehört jedem und heißt: kein Reittier.

- **Animation:** Stehen (Atmen, Schweif, Ohren, Schnauben), Gehen, Traben, Galopp im versetzten Viertakt beim Sprinten, Sprung, Landung, Schleichen, Schwimmen, Fallen. Alles zeitbasiert und weich überblendet. Der Reiter wippt mit, beugt sich im Galopp vor und hält die Zügel, solange er nichts benutzt oder schlägt.
- **Reaktionen:** Bei Schaden oder Emote hebt das Tier den Kopf. Streicheln mit `/mount` oder der Taste "Mount key" zeigt Freude und Herzen. `/mount` ist ein reiner Client-Befehl.
- **Effekte:** Funken, Glut, Blätter, Wolkenstaub, Sternenstaub und Staub bei der Landung. Dezent und abschaltbar.
- **Vorschau:** Im Shop und Inventar sitzt dein Spieler animiert im Sattel, mit Stand, Walk, Gallop, Jump und einem Regler zum Drehen.
- **Einstellungen** (Inventar und Goon Cosmetics): Size, Animation, Effects, Visible to others, Show in first person, Mount key, dazu die Anzeige "Mount render active: yes/no".
- **Sync:** Neues Feld `mount` im Backend und im Netzwerk-Paket (`cosmetics_v8`, Protokoll 8). Alte Clients ignorieren es, alte Einträge ohne das Feld gelten als "kein Reittier", unbekannte Ids werden nicht gezeichnet.
- **Leistung:** Höchstens 24 Reittiere gleichzeitig. Die aktuellen Entfernungsstufen stehen bei Update 3.80.0.
- **Texturen:** Reproduzierbar mit `tools/GenerateMounts.java`, die Modelle stehen in `MountModels.java`.

**Grenzen**

- `tools/backend/server.py` muss auf dem Backend ersetzt werden. Ohne das verwirft das alte Backend das Feld, andere Spieler sehen dein Reittier dann nicht.
- Andere Spieler sehen dein Reittier in normaler Größe, Size und Animation gelten nur auf deinem Bildschirm.
- Ob ein anderer Spieler sein Reittier wirklich besitzt, lässt sich nicht prüfen, wie bei allen Cosmetics. Es hat keinen Einfluss auf das Spiel.
- Vor einer Wand rutscht das Modell bis zu 0,55 Blöcke zurück. Bei langen Tieren kann der Kopf trotzdem in den Block ragen, in engen Gängen auch der Rumpf.
- Das Cape kann hinten durch das Tier gehen, ein Pop-Chams-Wireframe erscheint auf Höhe des Spielers ohne Anheben.
- Beim Elytra-Flug, Schlafen, Kriechen und Schwimmen im Spielerstil, in Booten und unsichtbar wird das Reittier ausgeblendet.
- Ein frei wählbares Namensschild für das Reittier gibt es noch nicht.

## Update 3.78.0: Wolken lassen sich wieder ausschalten

- **Fehler:** Mit einem Sky, der eigene Wolken hat (zum Beispiel Cotton Clouds), blieben diese sichtbar, obwohl in den Videoeinstellungen von Minecraft "Clouds: Off" eingestellt war.
- **Jetzt:** "Clouds: Off" gilt auch für die Wolken des Skys. Die Einstellung "Clouds" unter Goon Cosmetics schaltet sie weiterhin einzeln aus.
- **Vorschau:** In Shop und Inventar zeigt die Vorschau einen Sky immer mit seinen Wolken, damit man sieht, wie er aussieht.

## Update 3.77.0: Skys im normalen Goon Shop

- **Geändert:** Skys kommen jetzt in die normale stündliche Rotation des Goon Shops, wie alle anderen Items. Es gelten dieselben Seltenheits-Chancen und dieselben 8 Plätze.
- **Entfernt:** Den Tab "Hourly Shop", sein eigenes Angebot aus 6 Skys und den Zeitabgleich `GET /v1/time` gibt es nicht mehr. Der Goon Shop nutzt wie bisher die Uhr des PCs.
- **Rotation:** Weil 18 neue Items im Pool liegen, ändert sich die Auswahl der Rotation gegenüber älteren Versionen. Der Preis der Skys und ihr Inhalt bleiben gleich.
- **Besitz:** Bereits gekaufte Skys bleiben erhalten. Skys lassen sich jetzt wie andere Items aus dem Shop auch verschenken.

Die Abschnitte zu 3.75.0 und 3.76.0 unten beschreiben den damaligen Stand, dort stehen der Hourly Shop und `/v1/time` noch.

## Update 3.76.0: Codes mit Event-Coins

- **Neu:** Einlösbare Codes können jetzt neben Goon Coins auch Event-Coins geben, zum Beispiel Halloween Coins. Mit `add_code.py` zum Beispiel: `py -3 tools/backend/add_code.py 1000 --event-coins 500 --event-currency halloween`.
- **Ältere Clients:** Sie bekommen bei so einem Code die Meldung, dass sie GoonClient aktualisieren sollen. Der Code bleibt dabei unverbraucht.
- **Website:** Öffentliche Codes zeigen ihre Event-Coins jetzt auf der Karte, mit dem Hinweis "ab Version 3.76.0".
- **Backend:** `tools/backend/server.py`, `tools/backend/codes.json` und `tools/backend/site/index.html` müssen in `Goonboss1967/goonclient-backend` ersetzt werden. Der Client braucht mindestens Version 3.76.0.

## Update 3.75.0: Skys und der Hourly Shop

**Wichtig für das Backend:** `tools/backend/server.py` hat den neuen Endpunkt `GET /v1/time` und muss in `Goonboss1967/goonclient-backend` ersetzt werden (danach Manual Deploy auf Render). Ohne die neue Datei fehlt nur der Zeitabgleich des Hourly Shops: Der Client nutzt dann die Uhr des PCs, sonst funktioniert alles.

### Skys

Ein Sky ersetzt den Himmel der Overworld auf deinem eigenen Bildschirm. Alle Himmel laufen über einen einzigen prozeduralen Shader (`shaders/core/sky.fsh`), gesteuert über Daten in `cosmetics/sky/SkyCatalog.java`. Es gibt deshalb keine Bilddateien und kein Skript zum Erzeugen von Texturen, und die Vorschau zeigt genau das, was du im Spiel siehst.

| Sky | Id | Seltenheit | Preis | Besonderheit |
|---|---|---|---|---|
| Vanilla | `sky.vanilla` | Starter | frei | Normaler Himmel von Minecraft, gehört jedem |
| Clear Day | `sky.clearday` | Common | 40 | Klares Hellblau |
| Soft Dusk | `sky.softdusk` | Common | 55 | Pastellviolett |
| Night Blue | `sky.nightblue` | Common | 70 | Tiefes Marineblau, auch am Tag ruhig |
| Minimal Gray | `sky.minimalgray` | Common | 90 | Neutrales Grau |
| Morning Mist | `sky.morningmist` | Uncommon | 120 | Goldener Dunst am Horizont |
| Cotton Clouds | `sky.cottonclouds` | Uncommon | 150 | Weiche, ziehende Wolken |
| Teal Haze | `sky.tealhaze` | Uncommon | 190 | Türkis mit dünnen Schleiern |
| Starlit Plains | `sky.starlit` | Uncommon | 240 | Sternennacht mit schwachem Sternenband |
| Sunset Blaze | `sky.sunsetblaze` | Rare | 340 | Glühende Wolken und Sonnenstrahlen |
| Moonlit Lake | `sky.moonlitlake` | Rare | 420 | Großer Mond mit Kratern und Lichthof |
| Pink Dawn | `sky.pinkdawn` | Rare | 480 | Rosa Schichten, funkelnde Sterne |
| Emerald Bands | `sky.emeraldbands` | Rare | 580 | Grüne Wolkenbänder |
| Nebula | `sky.nebula` | Epic | 900 | Bunte Gaswolken, Sternschnuppen, Parallaxe |
| Aurora Night | `sky.auroranight` | Epic | 1150 | Fließendes Polarlicht |
| Ringed Planet | `sky.ringedplanet` | Epic | 1400 | Großer Planet mit Ring |
| Galaxy Core | `sky.galaxycore` | Legendary | 2400 | Spiralgalaxie, drei Monde, Sternschnuppen, Aurora |
| Eclipse | `sky.eclipse` | Legendary | 3000 | Sonnenfinsternis mit Korona und Strahlen |
| Celestial Gate | `sky.celestialgate` | Legendary | 3800 | Leuchtendes, drehendes Tor, Nebel, Aurora |

### Hourly Shop

- **Wo:** Im Goon Shop gibt es jetzt die Tabs "Items" (wie bisher, ohne Skys) und "Hourly Shop".
- **Angebot:** Jede volle Stunde (UTC) kommen 6 Skys ins Angebot, festgelegt allein durch die Stundennummer. Alle sehen zur selben Zeit dasselbe. Mindestens ein Common oder Uncommon ist immer dabei.
- **Chancen pro Platz:** Common 42,3 %, Uncommon 33 %, Rare 18 %, Epic 6 %, Legendary 0,7 %. Das ergibt im Mittel etwa ein Legendary pro Tag (im Test: 1,02).
- **Anzeige:** Countdown mit Fortschrittsbalken, Live-Vorschau auf den Karten. Neue Skys tragen in den ersten zwei Minuten der Stunde "NEW", gekaufte sind als "Owned" markiert.
- **Kauf:** Das Angebot wird beim Kauf selbst noch einmal geprüft. Wechselt die Stunde während der Bestätigung, wird der Kauf ohne Abzug abgelehnt. Gekaufte Skys gehören dir dauerhaft. Alte `wallet.json`-Dateien laden unverändert.
- **Zeit:** Der Client gleicht sich über `GET /v1/time` mit dem Server ab. **Das ist nicht fälschungssicher:** Das Backend kennt keine Käufe, und wer den Client verändert, kann das umgehen. Ohne Backend zählt die Uhr des PCs, dann lässt sich das Angebot auch durch Verstellen der Uhr ändern.

### Bedienung und Einstellungen

- **Inventar:** Tab "Skys" zum Ausrüsten und Ablegen, mit Live-Vorschau, Zeitregler und Knopf "Test in game". Der Knopf zeigt einen Sky 10 Sekunden lang, ohne ihn auszurüsten, wenn du in einer Welt bist. Der Knopf funktioniert auch im Shop, also vor dem Kauf.
- **Goon Cosmetics, Settings:** Auswahl mit "Locked"-Markierung und diese Einstellungen:

| Einstellung | Standard | Wirkung |
|---|---|---|
| Sky on | an | Aus: normaler Himmel, ohne den Sky abzulegen |
| Quality | High | Low, Medium oder High: weniger Rausch-Lagen, Polarlicht-Schichten und Sterne |
| Sky brightness | 100 % | 40 bis 120 %, nur die Optik des Himmels |
| Stars | an | Sterne des Skys |
| Clouds | an | Wolken des Skys |
| Sky in rain | an | Aus: Bei Regen blendet der normale Himmel ein |
| Minecraft clouds | aus | Zeigt zusätzlich die normalen Wolken |

Darunter steht die Diagnose "Sky render active".

### Verhalten

- **Tageszeit:** Der Sky folgt dem Sonnenstand von Minecraft mit weichen Übergängen zwischen Morgen, Tag, Abend und Nacht.
- **Wetter:** Regen und Gewitter machen ihn grauer und dunkler, Sterne und Effekte verschwinden.
- **Andere Orte:** Nether, End und Sicht unter Wasser bleiben unverändert. In Höhlen, unter dem Horizont der Welt, bleibt der normale Nebel.
- **Nebel:** Über Tage bekommt der Nebel die Horizontfarbe des Skys, damit es keinen Bruch zum fernen Gelände gibt. Nur die Farbe ändert sich, nicht die Sichtweite.

### Fairness

Skys sind rein kosmetisch und werden nicht an andere Spieler gesendet. Sie ändern weder die Helligkeit der Welt noch Licht, Sichtweite, Reichweite, Mobs oder Wetter. Das ist kein Fullbright und kein Vorteil. Die Regeln einzelner Server können sich trotzdem unterscheiden.

### Grenzen

- **Mondphasen:** Skys zeigen immer den vollen Mond.
- **Normale Wolken:** Standardmäßig sind sie bei aktivem Sky ausgeblendet, weil weiße Wolken vor einem Weltraum-Himmel unpassend wirken. "Minecraft clouds" bringt sie zurück.
- **Parallaxe:** Sie ist ein leichtes Mitdrehen der Schichten mit der Kamera, keine echte Tiefe.
- **Optionale Aktionspreise:** Der Hourly Shop zeigt nur Skys, keine Items aus anderen Kategorien.
- **Getestet und nicht getestet:** Im Spiel geprüft sind alle 18 Skys auf Kontaktbögen zu vier Tageszeiten, zehn davon auch in der Welt, außerdem Kaufregeln, Regen, Wasser, Nether und Menüs. **Nicht** geprüft sind schwache Grafikkarten, AMD- und Intel-Treiber, Shader-Mods wie Iris, hohe Auflösungen und ein echter Server. Die Bildrate lag im Test mit und ohne Sky bei etwa 118, aber in einem kleinen Fenster und nahe an einer Begrenzung. Das sagt also wenig über die Last aus. Bei Problemen hilft Quality "Low" oder "Sky on" aus.

### Technik

- **Eingriffe:** `SkyRendererMixin` (`renderSkyDisc`, `renderSunriseAndSunset`, `renderSunMoonAndStars`, `renderDarkDisc`), `FogRendererMixin` (`computeFogColor`), `LevelRendererMixin` (`addCloudsPass`), alle mit `require = 0`. Scheitert der Shader, bleibt der normale Himmel.
- **Reine Logik:** `SkyDef`, `SkyCatalog`, `SkyMath` und `shop/SkyShop`, getestet von `tools/SkyLogicTest.java`.
- **Neuer Sky:** Ein Eintrag in `SkyCatalog` genügt.

## Update 3.74.0: Pop Chams ohne "Through walls"

- **Entfernt:** Die Option "Through walls" gibt es nicht mehr. Der eigene Zeichenweg ohne Tiefentest ist aus dem Code raus. War die Option bei dir an, gilt sie nicht mehr.
- **Wireframe und Shell:** Blöcke verdecken das Gitter und die Hülle immer ganz normal, auch nur teilweise.
- **Outline:** Der Umriss nutzt das Glow-System von Minecraft, und das kennt keine Wände. Er erscheint deshalb nur, wenn die Sichtlinie zu Füßen, Körpermitte oder Kopf frei ist. Hinter einer Wand leuchtet er auch beim Pop nicht mehr kurz auf. **Grenze:** Ragt jemand halb hinter einer Kante hervor, ist der ganze Umriss zu sehen, also auch der Teil hinter der Kante. Geht jemand hinter eine Wand, blendet der Umriss noch bis zu etwa 0,2 Sekunden aus. Wer das vermeiden will, bleibt beim Standard Wireframe.
- **Pop counter:** Die Chat-Zeile erscheint weiterhin für jeden Pop innerhalb der Reichweite, auch hinter Wänden. Sie zeigt nur, was Minecraft dem Client ohnehin meldet. Abschaltbar mit "Pop counter".

Die älteren Abschnitte unten beschreiben den damaligen Stand, dort steht "Through walls" noch.

## Update 3.73.0: Pop Chams im Wireframe-Look

Neuer Darstellungsmodus **Wireframe**, jetzt der Standard: Beim Totem-Pop bleibt ein leuchtendes Drahtgitter in der Pose des Spielers genau an dieser Stelle stehen, während der echte Spieler sich wegbewegen kann. Jeder der sechs Körperteile ist ein eigener Quader, von dem nur die 12 Kanten zu sehen sind. Outline und Shell gibt es weiterhin.

### Ablauf

Die Linien blitzen kurz heller und dicker auf, bleiben kurz stabil und blenden dann weich aus. Dabei steigt das Gitter um etwa 6 Zentimeter und wächst um 3 Prozent. Ein zweiter Pop desselben Spielers erzeugt ein zweites Gitter. Beim Tod, beim Respawn und beim Weltwechsel oder Disconnect verschwinden die Gitter sofort.

### Neue und geänderte Einstellungen

| Einstellung | Standard | Wirkung |
|---|---|---|
| Display | Wireframe | Wireframe, Outline oder Shell |
| Color 1 (top), Color 2 (bottom) | #3FD0FF, #0A8FE0 | Verlauf von oben nach unten |
| Line width | 2,5 | Liniendicke in Bildschirmpixeln, 1 bis 6, in jeder Entfernung gleich |
| Effect opacity | 85 % | Deckkraft |
| Effect duration | 2,0 s | Dauer, 0,5 bis 5 s |
| Inflate | 8 % | So viel größer als der Körper ist jeder Quader, 0 bis 20 % |
| Corner points | an | Feine, etwas hellere Punkte auf den Ecken |
| Rise | an | Gitter steigt beim Ausblenden etwas auf |
| Pulse | an | Gitter wächst langsam ein wenig |
| Flash | an | Aufblitzen am Anfang |
| Max ghosts | 6 | Gleichzeitige Gitter, 1 bis 16. Das älteste verschwindet zuerst |
| Particle burst | **aus** | Eigener Partikelburst, jetzt standardmäßig aus. Die Totem-Partikel von Minecraft bleiben |

Regenbogen, Farbe nach Beziehung, "Through walls", "Show own pops", "Show others' pops" und "Range" gelten auch für das Wireframe. In der Diagnose steht zusätzlich "Wireframe render active: yes/no, snapshots: N".

**Beim Update:** Damit der neue Look sofort stimmt, haben Display, die beiden Farben, Dauer, Deckkraft und der Partikelburst neue Namen und neue Standardwerte. Wer diese Pop-Chams-Werte in 3.72.0 geändert hatte, muss sie neu einstellen.

### Fairness

Das Modul ist rein visuell, zeigt nur Informationen, die der Client ohnehin erhält, und sendet nichts an den Server. **Manche Server verbieten Anzeigen durch Wände.** Deshalb ist "Through walls" standardmäßig aus, und das Gitter wird dann normal von Blöcken verdeckt.

### Grenzen

- **Nur Spieler:** Andere Lebewesen bekommen kein Gitter.
- **Keine Biegung:** Gebeugte Ellbogen und Knie aus Emotes zeigt das Gitter gerade, weil jeder Körperteil genau ein Quader ist.
- **Ohne Hut und Überzug:** Das Gitter folgt dem Grundmodell. Überzüge wie Hut oder Ärmel haben keine eigenen Linien.
- **Bildwinkel:** Die Liniendicke rechnet mit dem eingestellten FOV. Während eines FOV-Effekts wie beim Sprinten weicht sie minimal ab.
- **Shader-Mods:** Das Zusammenspiel mit Iris oder ähnlichen Mods ist nicht getestet.

### Technik

- **Daten:** `popchams/WireGhost` und `WireGhosts` kommen ohne Minecraft-Klassen aus und werden von `tools/WireframeLogicTest.java` getestet. Die 48 Eckpunkte werden beim Pop einmal berechnet und sind danach feste Zahlen.
- **Schnappschuss:** `WireframeRenderer.snapshot` holt beim Pop einen eigenen Render-Zustand des Spielers und baut die Matrix wie `LivingEntityRenderer.submit`. Die dafür nötigen geschützten Methoden erreicht er über `LivingEntityRendererInvoker`.
- **Linien:** Minecrafts Linien-Renderer wird nicht verwendet. Jede Kante ist ein schmales, zur Kamera zeigendes Band mit weichem Rand und schwachem Schein. Das gibt freie Dicke, Verlauf und glatte Kanten ohne Treppen.
- **Tiefe:** Normaler Tiefentest mit kleiner Tiefenverschiebung, bei "Through walls" ohne Tiefentest.

## Update 3.72.0: Neues Modul Pop Chams

Verbraucht ein Spieler ein Totem, leuchtet kurz eine Umrandung oder Hülle um seinen Körper auf: erst ein kurzes Aufleuchten, dann stabil, dann weiches Ausblenden. Das Modul liegt in der Kategorie Render und ist standardmäßig aus. Dazu gibt es das neue HUD-Modul **Pop Counter** ("Pops: N"), das deine eigenen Pops seit deinem letzten Tod zählt. Es braucht Pop Chams.

### Darstellungsarten

- **Outline (Standard):** Nutzt das Glow-System von Minecraft. Jeder Umriss blendet einzeln aus, ohne dabei schwarz zu werden.
- **Shell:** Eine leicht vergrößerte, leuchtende Hülle um das aktuell posierte Spielermodell. Kanten und flach zur Kamera stehende Seiten sind heller als die Fläche. Am Anfang dehnt sie sich kurz aus. Vor hellem Himmel bleibt die Farbe erhalten, deshalb ist die Überblendung nicht rein additiv.

### Einstellungen

| Einstellung | Standard | Wirkung |
|---|---|---|
| Mode | Outline | Outline oder Shell |
| Duration | 1,5 s | Dauer des Effekts, 0,5 bis 5 s |
| Strength | 100 % | Helligkeit, 25 bis 200 % |
| Thickness | 0,75 | Abstand der Hülle zum Körper in Modellpixeln, nur bei Shell |
| Opacity | 100 % | Deckkraft, 10 bis 100 % |
| Pulse | an | Hülle dehnt sich kurz aus, nur bei Shell |
| Color 1, Color 2, Use color 2 | Gelb, Grün, an | Verlauf: beim Umriss über die Zeit, bei der Hülle von oben nach unten |
| Rainbow | aus | Läuft durch alle Farben |
| Color by relation | aus | Eigene Farben für dich, Freunde, andere Spieler und Gegner |
| Show own pops, Show others' pops | an | Wessen Pops zu sehen sind. Eigene siehst du nur in der Außenansicht |
| Through walls | **aus** | Effekt auch hinter Wänden |
| Range | 64 | Reichweite in Blöcken, 8 bis 256 |
| Pop counter | an | "Player popped 2 totems" im Chat. Schreibt Totem Tweaks das schon, kommt es nicht doppelt |
| Particles | an | Kleiner Partikelburst in der Effektfarbe |
| Sound | aus | Kurzer, leiser Klang zusätzlich zum Totem-Sound |
| Test effect | | Spielt den Effekt an dir selbst ab, zu sehen mit F5 |

Darunter zeigt eine Diagnose, wie viele Pops erkannt wurden und ob die Render-Hooks greifen. Als **Gegner** gilt, wer in einem anderen Scoreboard-Team ist als du. Freunde kommen aus der GoonClient-Friendlist.

### Fairness

Das Modul ist rein visuell und zeigt nur Informationen, die der Client ohnehin erhält. Es verändert keine Spielmechanik und sendet nichts an den Server. **Manche Server verbieten Client-Mods mit Wallhack-Wirkung.** Deshalb ist "Through walls" standardmäßig aus. Prüfe die Regeln des Servers, bevor du es einschaltest. Unsichtbare Spieler bekommen keinen Effekt.

### Grenzen

- **Nur Spieler:** Andere Lebewesen, die ein Totem benutzen, bekommen keinen Effekt.
- **Umriss und Wände:** Das Glow-System kennt keine Wände. Ist "Through walls" aus, prüft das Modul deshalb 20-mal pro Sekunde die Sichtlinie zu Füßen, Körpermitte und Kopf. Ist ein Punkt sichtbar, erscheint der ganze Umriss, also auch der Teil hinter einer Kante. Die Hülle hat dieses Problem nicht.
- **Umrissbreite:** Die Breite gibt Minecraft fest vor. "Thickness" gilt nur für die Hülle.
- **Andere Glow-Effekte:** Solange ein Pop-Umriss läuft, wirkt auch jeder andere Glow (zum Beispiel Spektralpfeile) über dieselbe Überblendung etwas anders. Schwarze Team-Umrisse sind in dieser Zeit nicht zu sehen.
- **Shader-Mods:** Ob Umriss und Hülle mit Iris oder ähnlichen Mods laufen, ist nicht getestet.
- **Höchstens 16 Effekte gleichzeitig.** Ein neuer Pop verdrängt dann den ältesten. Beim Tod, beim Verschwinden eines Spielers, beim Weltwechsel und beim Disconnect werden Effekte sofort entfernt.

### Technik

- **Logik:** `popchams/PopTracker` kommt ohne Minecraft-Klassen aus und wird von `tools/PopChamsLogicTest.java` getestet.
- **Erkennung:** Entity-Event 35 in `ClientPacketListener.handleEntityEvent`.
- **Umriss:** `state.outlineColor` im `extractRenderState` und eine eigene Überblendung (`shaders/core/pop_outline_blit.fsh`) in `LevelRenderer.doEntityOutline`. Fehlt dieser Eingriff, bleibt der Umriss sichtbar, wird beim Ausblenden aber dunkel.
- **Hülle:** `PopChamsRenderer` zeichnet sie über einen eigenen Render-Typ aus `AccessoryLayer`.
- **Neu im Menü:** Der Einstellungstyp `InfoSetting` zeigt die Diagnose.

## Update 3.71.0: Fenster "What's new" nach jedem Update

- **Fenster:** Beim ersten Start nach einem Update öffnet sich im Hauptmenü einmalig ein Fenster, das zeigt, was neu ist. Mit "Got it", Enter oder Esc schließt du es, das Mausrad scrollt.
- **Übersprungene Versionen:** Wer mehrere Updates ausgelassen hat, sieht bis zu 5 Versionen auf einmal, die neueste zuerst.
- **Wieder öffnen:** Ein Klick auf die Versionsnummer oben links im GoonClient-Menü zeigt alle Texte.
- **Wer es nicht sieht:** Bei einer Neuinstallation erscheint kein Fenster. Es gilt erst ab dem nächsten Update.
- **Umstieg auf 3.71.0:** Ältere Versionen haben nicht gespeichert, was du zuletzt gesehen hast. Bestehende Spieler sehen deshalb einmal nur den Text von 3.71.0.
- **Für jedes neue Update:** Trage den Text in `src/client/resources/assets/goonclient/whatsnew.json` ein (`version`, `title` und mindestens eine der Listen `new`, `improved`, `fixed`). Fehlt der Eintrag für die Version aus `gradle.properties`, bricht der Build mit einer Fehlermeldung ab.
- **Tests:** `tools/WhatsNewTest.java` prüft die Auswahl der Versionen und die Datei selbst.

## Update 3.70.0: Hochwertige Emotes, 14 neue und alle überarbeitet

**Wichtig für das Backend:** `tools/backend/server.py` hat die neuen Emote-Ids bekommen und muss in `Goonboss1967/goonclient-backend` ersetzt werden (danach Manual Deploy auf Render). Ohne die neue Datei lehnt der Server die 14 neuen Emotes ab: Du siehst sie weiter bei dir selbst, aber andere Spieler sehen sie nicht. Die 18 alten Emotes funktionieren auch mit dem alten Server.

### Alle Emotes

Die Ids der alten Emotes sind gleich geblieben. Besitz und Radbelegung bleiben also erhalten. Alle 18 alten Emotes sind neu animiert: mit Ausholen, Überschwingen, Ausklingen und Bewegung im ganzen Körper.

| Emote | Id | Seltenheit | Preis | Neu |
|---|---|---|---|---|
| Wave | `wave` | Common | 25 | |
| Thumbs Up | `thumbsup` | Common | 35 | |
| Salute | `salute` | Common | 40 | |
| Point | `point` | Common | 45 | |
| Heartbeat | `heartbeat` | Common | 50 | ja |
| Shrug | `shrug` | Common | 55 | |
| Hero Pose | `hero` | Common | 60 | ja |
| Clap | `clap` | Uncommon | 100 | |
| Sleep | `sleep` | Uncommon | 110 | ja |
| Think | `think` | Uncommon | 120 | |
| Meditate | `meditate` | Uncommon | 130 | ja |
| Facepalm | `facepalm` | Uncommon | 140 | |
| Rage | `rage` | Uncommon | 150 | ja |
| Bow | `bow` | Rare | 240 | |
| Tiny Head | `tinyhead` | Rare | 240 | ja |
| Flex | `flex` | Rare | 280 | |
| Confetti | `confetti` | Rare | 280 | ja |
| Dab | `dab` | Rare | 300 | |
| Cheer | `cheer` | Rare | 320 | |
| Bounce | `bounce` | Rare | 340 | ja |
| Balloon | `balloon` | Rare | 380 | ja |
| Ghostly | `ghostly` | Epic | 600 | ja |
| Spin | `spin` | Epic | 650 | |
| Big Head | `bighead` | Epic | 780 | ja |
| Dance | `dance` | Epic | 800 | |
| Backflip | `flip` | Epic | 900 | ja |
| Power Up | `fire` | Legendary | 1600 | ja |
| Levitate | `levitate` | Legendary | 1800 | |
| Mind Blown | `mindblown` | Legendary | 2200 | ja |

Dazu kommen drei alte Emotes außerhalb des normalen Verkaufs, Preis und Herkunft sind unverändert: Zombie Walk (`zombie`, Common, 150, limitiert), Boo! (`boo`, Rare, 480, limitiert) und Robot (`robot`, Rare, 300, Saison). Insgesamt sind es 32 Emotes.

### Bedienung

- **Rad:** Taste halten (Standard B), mit der Maus ein Feld wählen, loslassen oder klicken. Das Rad hat jetzt 3 Seiten mit je 8 Feldern. Die Seite wechselst du mit dem Mausrad oder den Pfeiltasten. Die Belegung stellst du im Inventar ein, dort gibt es dafür die Knöpfe `<` und `>`.
- **Vorschau im Shop und Inventar:** Die Figur spielt das ganze Emote in Schleife, mit Effekten. In der großen Ansicht zeigt eine Zeitleiste den Fortschritt, die Marken darauf stehen für die Effekte.
- **Abbrechen:** Ein Emote blendet in 0,3 Sekunden weich aus. Startest du ein neues, blendet das alte in 0,28 Sekunden über.

### Neue Einstellungen im Modul Emotes

| Einstellung | Standard | Wirkung |
|---|---|---|
| Effects | an | Partikel und Symbole bei Emotes |
| Effect strength | 100 % | Menge der Partikel, 25 bis 150 % |
| Cooldown | 1 s | Wartezeit bis zum nächsten eigenen Emote, 0 bis 10 s. Der Backflip wartet immer mindestens 3 s |
| Third person while emoting | aus | Schaltet während des eigenen Emotes auf die Frontansicht und danach zurück |

### Grenzen

- **Skalierung:** Der Kopf bleibt zwischen 0,2- und 3-fach, der Rumpf zwischen 0,6- und 1,9-fach, die ganze Figur zwischen 0,5- und 1,6-fach. Diese Grenzen gelten beim Anzeigen für jeden Spieler. Der Backflip steigt höchstens 1 Block hoch.
- **Entfernung:** Bis 32 Blöcke siehst du Animation und Effekte, ab 32 Blöcken nur die Animation, ab 64 Blöcken nichts mehr.
- **Effekte:** Sie sind Sprites, keine Welt-Partikel. Sie gehören zur Figur und drehen sich mit ihrem Körper. Ton gibt es keinen.
- **Erste Person:** Deine Arme bewegen sich in der Ego-Sicht nicht mit. Das Emote siehst du nur von außen, zum Beispiel mit F5 oder der neuen Kamera-Option.
- **Ghostly** macht die Figur nicht wirklich durchsichtig, weil das nicht sauber ging. Stattdessen schwebt sie in kaltem Nebel.
- **Abbruch und Besitz bei anderen:** Das Backend überträgt nur den Start eines Emotes. Brichst du ab, spielen andere es zu Ende. Ob jemand ein Emote wirklich besitzt, kann dein Client nicht prüfen, weil Wallets nur lokal liegen. Unbekannte Ids werden ausgeblendet.
- **Goon Shop:** Die neuen Emotes kommen auch in die stündliche Rotation. Deshalb ändert sich deren Auswahl einmalig gegenüber der Vorversion.

### Getestet und nicht getestet

- **Getestet:** Alle 32 Emotes liefen im echten Spiel und wurden zu je 6 Zeitpunkten auf Kontaktbögen geprüft. Dazu kamen Abbruch, Cooldown, Kamera-Option, Rad-Seiten und die Vorschau im Inventar. `tools/EmoteLogicTest.java` prüft Stetigkeit, neutrale Enden, NaN, Grenzen, die nahtlose Dance-Schleife, Effekt-Marken, Katalog und alte Wallets.
- **Nicht getestet:** Die Anzeige bei einem echten zweiten Spieler, also auch die Entfernungsstufen und das angehobene Namensschild beim Riesenkopf. Die Flüssigkeit wurde nicht als Video geprüft, sondern nur rechnerisch und auf Einzelbildern.

### Technik

- `EmoteEngine.Pose` hat neue Felder für Kopf-, Rumpf- und Gesamtskalierung, Neigung, Überschlag und Versatz. `xScale`, `yScale` und `zScale` von `ModelPart` gibt es in 1.21.11, das hat der Compiler bestätigt.
- Dazu kommen Easing (`Ease`) und Keyframes (`Key`, `track`) sowie der eigene Effekt-Spieler `EmoteFx` mit Daten statt Code. Der Partikel-Atlas hat eine vierte Reihe: Fragezeichen, Z, Note, Schlag, Konfetti, Ausrufezeichen, Rauch und Druckwelle.
- Das Rad hat in der Wallet 24 Plätze. Alte Wallet-Dateien laden weiter und ihre Signatur bleibt gültig, solange die Seiten 2 und 3 leer sind.

## Update 3.69.0: Auren springen beim Sprung nicht mehr

- **Fehler:** Beim Absprung sprangen alle Teilchen einer Aura im selben Moment bis zu 4 Pixel nach außen und wurden schlagartig heller. Das sah aus, als würde die Animation neu starten.
- **Jetzt:** Der Sprung-Impuls schwillt in 0,15 Sekunden weich an und läuft bis 0,6 Sekunden wieder aus. Das gilt für alle Auren. Auch das schnelle Hüpfen löst keinen Sprung im Impuls mehr aus.
- **Tests:** `tools/AuraEngineTest.java` prüft für jede Aura, dass beim Absprung kein Teilchen von Bild zu Bild springt.

**Hochladen:** den Ordner `tools/backend/site`, danach "Manual Deploy" auf Render. `server.py` hat sich gegenüber 3.68.0 nicht geändert.

## Update 3.68.0: 6 neue Haustiere

| Pet | Id | Seltenheit | Preis | Art | Eigenheit |
|---|---|---|---|---|---|
| Wolf Pup | `pet.wolfpup` | Common | 60 | läuft | trabt verspielt, Schwanz wedelt immer, springt höher mit, heult im Stand ab und zu (nur Animation, kein Sound) |
| Panda | `pet.panda` | Uncommon | 150 | läuft | schaukelnder Gang, setzt sich im Stand und kaut Bambus, rollt sich beim Streicheln zur Seite |
| Axolotl | `pet.axolotl` | Rare | 280 | schwebt | Welle durch den Körper, sechs Kiemen wippen und legen sich beim Tempo an, im Wasser schneller |
| Slimey | `pet.slimey` | Rare | 360 | hüpft | durchscheinend mit Kern, Squash und Stretch, Spritzer bei der Landung, wählbar Grün, Blau, Pink |
| Owl | `pet.owl` | Epic | 780 | fliegt | ruhige Flügelschläge, dreht den Kopf weit, blinzelt langsam, setzt sich auf die Schulter, wenn der Spieler steht |
| Phoenix Chick | `pet.phoenixchick` | Legendary | 1800 | hüpft | flattert beim Hüpfen, Glut-Funken, leuchtet immer und beim Streicheln stärker |

- **Kaufen:** wie alle Items über die stündliche Rotation des Goon Shops. Alte Wallets laden weiter.
- **Einstellungen:** `Size`, `Animation`, `Effects`, `Visible to others`, `Pet key` und neu `Slimey color`. Du findest sie im Inventar unter `Pets` und in `Goon Cosmetics > Settings > Pet`,
  dort auch die Pet-Auswahl mit `Locked`. Sie gelten für das ausgerüstete Pet, nicht je Pet. Alte Configs laden weiter (Slimey ist dann grün).
- **Sync:** Die Pet-Ids laufen über das vorhandene Feld `pet`, alte Clients ignorieren unbekannte Pets. Die Farbe von Slimey steckt in `petStyle` (Bits 17 und 18).
  Fremder Besitz lässt sich nicht prüfen, wie bei allen Items.
- **Grenzen:**
  - Kein Pet-Name als Namensschild (optional im Auftrag, weggelassen: freier Text an andere Spieler bräuchte ein neues Protokollfeld und Moderation).
  - Die Eule setzt sich nicht auf die Schulter, solange du in der Ego-Ansicht bist, und folgt dabei nicht der Armhaltung.
  - Die Vorschau im Menü zeigt die Idle-Animation, ohne Maus zum Drehen.
  - Streicheln sehen nur du selbst, und jeder Client berechnet die Tiere selbst, sie stehen bei zwei Spielern nie exakt gleich.
  - Der Axolotl schwimmt schneller, wenn der Spieler im Wasser ist, nicht abhängig vom eigenen Standort.
- **Modelle und Texturen:** `PetModels.java` und `tools/GeneratePets.java` (neue Muster: Federn, Schleim, Flaum, Bambus, Fransen).
- **Tests:** `tools/PetAnimatorTest.java` prüft alle 14 Pets (Winkel, NaN, Übergänge, Federung, Abstand, Gelände, Schweben), dazu Katalog, Preisbänder, Kauf, Schulter, Sitzen, Schleim-Volumen und Farbe.
  Backend-Rundlauf in `tools/BackendIntegrationTest.java` und `tools/backend/test_backend.py`.

**Hochladen:** `tools/backend/server.py` im Repo `Goonboss1967/goonclient-backend` ersetzen und den Ordner `tools/backend/site` hochladen, danach "Manual Deploy" auf Render.
Ohne die neue `server.py` sehen andere Spieler auf Servern ohne GoonClient-Relay dein Slimey immer grün. Die Pets selbst funktionieren auch mit der alten `server.py`.

## Update 3.67.0: BETA-Schild im Menü

- Ganz oben rechts auf dem GoonClient-Menü steht jetzt `BETA`, daneben "Found a bug? Please report it!". Bei sehr schmalem Fenster bleibt nur `BETA`.

**Hochladen:** den Ordner `tools/backend/site`, danach "Manual Deploy" auf Render. `server.py` hat sich nicht geändert.

## Update 3.66.0: Laufende Haustiere schweben nicht mehr

- **Fehler:** Laufende Haustiere konnten in der Luft oder auf Dächern hängen bleiben. Die Bodensuche begann in der Höhe des Tiers und reichte nur 6 Blöcke nach unten; fand sie nichts,
  blieb das Tier, wo es war. Das passierte zum Beispiel nach Sprungplatten oder Teleports. Jeder Client berechnet das Tier selbst, deshalb sahen es manche Spieler und andere nicht.
- **Jetzt:** Der Boden wird immer ab der Höhe des Spielers gesucht, bis zu 96 Blöcke tief. Ohne Boden in Reichweite läuft das Tier auf Höhe des Spielers.
- **Dauer-Teleport behoben:** Unter einem mehr als 10 Blöcke hoch fliegenden Spieler teleportierte das Tier in jedem Bild neu (mit Partikeln). Es teleportiert jetzt nur, wenn es dadurch näher kommt.
- **Tests:** `tools/PetAnimatorTest.java` prüft Landen nach dem Hochschleudern, Dach und fliegenden Spieler.
- **Wichtig:** Jeder Spieler berechnet die Tiere der anderen selbst. Damit jemand dein Tier richtig sieht, braucht diese Person selbst 3.66.0.

**Hochladen:** den Ordner `tools/backend/site`, danach "Manual Deploy" auf Render. `server.py` hat sich nicht geändert.

## Update 3.65.0: Haustier-Schatten sichtbar

- Der weiche Schatten laufender Haustiere war seit 3.60.0 zu klein und zu blass und lag fast ganz unter dem Tier. Er ist jetzt größer und kräftiger und wächst mit `Size`.
- Fliegende Haustiere haben weiterhin keinen Schatten.

**Hochladen:** den Ordner `tools/backend/site`, danach "Manual Deploy" auf Render. `server.py` hat sich nicht geändert.

## Update 3.64.0: Eigene Aura nie in der Ego-Ansicht

- In der Ego-Ansicht siehst du deine eigene Aura jetzt nie, die Auren anderer GoonClient-Spieler aber weiterhin. In der Third Person (F5) siehst du deine Aura wie bisher.
- Der Schalter `Third person only` aus 3.63.0 ist entfernt, er wird nicht mehr gebraucht. Alte Configs laden weiter, der gespeicherte Wert wird ignoriert.

**Hochladen:** den Ordner `tools/backend/site`, danach "Manual Deploy" auf Render. `server.py` hat sich nicht geändert.

## Update 3.63.0: 16 neue Auren

| Aura | Id | Seltenheit | Preis | Look |
|---|---|---|---|---|
| Sakura | `aura.sakura` | Common | 55 | Blütenblätter segeln in S-Kurven herab |
| Autumn Leaves | `aura.leaves` | Common | 60 | Herbstblätter wirbeln, wehen beim Laufen hinterher |
| Soap Bubbles | `aura.bubbles` | Uncommon | 110 | Seifenblasen steigen, wackeln und platzen mit Spritzer |
| Fireflies | `aura.fireflies` | Uncommon | 130 | Glühwürmchen auf Lissajous-Bahnen mit weichem Puls |
| Stardust | `aura.stardust` | Rare | 240 | Sternenstaub-Band windet sich hoch, Sterne blinken |
| Rain Cloud | `aura.rain` | Rare | 300 | Wolke über dem Kopf, Tropfen, Spritz-Ringe, leises Leuchten |
| Sandstorm | `aura.sandstorm` | Rare | 340 | Sandkörner in einem Trichter, Staubringe am Boden |
| Northern Lights | `aura.aurora` | Rare | 390 | Polarlicht-Vorhänge wehen hinter und neben dir |
| Petal Storm | `aura.petalstorm` | Epic | 620 | Drei Blüten-Umlaufbahnen, Windstöße beim Sprinten |
| Crystal Orbit | `aura.crystalorbit` | Epic | 720 | Kristalle in drei Größen kreisen und blitzen auf |
| Blade Wind | `aura.bladewind` | Epic | 860 | Drei Klingenbögen schneiden in Wellen, mit Funken |
| Holo Field | `aura.holo` | Epic | 980 | Daten-Ringe, Gitter, Scan-Ring, kurze Glitches |
| Galaxy | `aura.galaxy` | Legendary | 1700 | Spiralgalaxie hinter dir: Kern, Arme, ferne Sterne |
| Celestial | `aura.celestial` | Legendary | 1950 | Heiligenschein, Strahlenkranz, schwebende Lichtfedern |
| Phoenix Fire | `aura.phoenixfire` | Legendary | 2300 | Schlagende Flammenflügel, Federn zerfallen zu Glut, Feuerstoß beim Springen |
| Eclipse | `aura.eclipse` | Legendary | 2800 | Dunkle Scheibe mit brennender Korona, Strahlen, Funken |

Die sieben alten Auren bleiben unverändert im Katalog: Love (140), Frost (340), Matrix (380), Flame (800), Lightning (900), Golden Rings (1900), Void (2400).

- **Ids:** `crystalorbit` und `phoenixfire` heißen so, weil `crystals` (Accessoire) und `phoenix` (Flügel) schon vergeben sind.
- **Kaufen:** wie alle Items über die stündliche Rotation des Goon Shops. Starter-Auren gibt es keine.
- **Einstellungen:** `Intensity`, `Size`, `Speed`, `Custom colors` mit `Color 1` und `Color 2` (bei Crystal Orbit die Kristallfarbe), `Visible to others`
  und neu `Third person only`. Du findest sie im Inventar unter `Auras` und in `Goon Cosmetics > Settings > Aura`, dort auch die Aura-Auswahl mit `Locked`.
  Sie gelten für die ausgerüstete Aura, nicht je Aura. Alte Configs laden weiter.
- **Fehler aus früheren Updates behoben:** Die Einstellungen von Auren und Haustieren (auch `Pet key`) gab es seit 3.59.0 bzw. 3.60.0 zwar, sie standen aber in
  keinem Menü. Jetzt stehen sie im Inventar. Dazu erkennen Auren die Bewegung anderer Spieler jetzt richtig.
- **Überblendung:** Hauptformen werden deckend-weich gezeichnet, nur Glanz und Funken additiv. Rein additive Teilchen wären vor hellem Himmel weiß und kaum zu sehen.
  Alte Auren profitieren davon bei ihren dunklen Teilchen.
- **Sicht:** Scheiben im Rücken (Galaxy, Eclipse) werden durchsichtig, wenn du von hinten schaust, damit der Spieler sichtbar bleibt.
- **Leistung:** höchstens 70 Teilchen je Aura und Spieler, keine Objekte pro Bild in der Berechnung, ab 16 Blöcken weniger Teilchen, bei 32 Blöcken noch 20 %, ab 64 keine.
- **Grenzen:**
  - Ringe am Boden (Rain Cloud, Sandstorm, Crystal Orbit) liegen auf Fußhöhe und folgen nicht dem Gelände, beim Springen oder an Kanten schweben sie.
  - Beim Schwimmen, Gleiten oder in Emotes bleibt die Aura aufrecht am Spieler und kippt nicht mit.
  - Teilchen leuchten immer gleich hell, auch nachts und in Höhlen.
  - Fremder Besitz lässt sich nicht prüfen, wie bei allen Items.
- **Texturen:** `java tools/GenerateAuraParticles.java` schreibt `textures/aura/atlas.png` und den Kontaktbogen `build/aura_particles.png`. Es ersetzt `tools/GenerateAuraAtlas.java`.
  Alle Bilder sind selbst berechnet.
- **Tests:** `tools/AuraEngineTest.java` prüft zusätzlich: Obergrenze wird nie erreicht (kein Teilchen reißt ab), Silhouette bleibt sichtbar, kein Sprung beim Wechsel von
  Sprinten und Laufen, mindestens drei Bilder je Aura, Katalog, Preisbänder, Kauf. Backend-Rundlauf in `tools/BackendIntegrationTest.java` und `tools/backend/test_backend.py`.

**Protokoll und Backend:** Keine Änderung nötig. Aura-Ids laufen schon über das Feld `aura`, alte Clients ignorieren unbekannte Ids. `server.py` hat sich gegenüber 3.61.0 nicht geändert.

**Hochladen:** den Ordner `tools/backend/site`, danach "Manual Deploy" auf Render. `tools/backend/server.py` nur, falls die Version aus 3.61.0 noch nicht online ist.

## Update 3.62.0: Schriften in der stündlichen Rotation

- Der eigene Tab `Fonts` im Goon Shop ist wieder weg. Schriften kommen jetzt wie alle anderen Items zufällig in die 8 Plätze der
  stündlichen Rotation, mit denselben Chancen je Seltenheit. Außerhalb ihrer Stunde sind sie nicht kaufbar. Mit "Show locked" im
  Inventar lassen sie sich auf die Wunschliste setzen.
- Im Inventar bleibt die Kategorie `Fonts`, dort rüstest du gekaufte Schriften aus. Default gehört weiter jedem und ist nie im Shop.
- Weil mehr Items im Pool sind, sehen Clients ab 3.62.0 pro Stunde einen anderen Shop als ältere Versionen.

**Hochladen:** den Ordner `tools/backend/site`, danach "Manual Deploy" auf Render. `server.py` hat sich gegenüber 3.61.0 nicht geändert.

## Update 3.61.0: Schriften im Goon Shop

Neue Shop-Kategorie **Fonts**: Du kaufst eine Schrift mit Goon Coins und rüstest sie im Inventar aus. Sie gilt für deinen Namen über dem
Kopf, im Chat und in der Tab-Liste und funktioniert zusammen mit Nametag-Farben, Animationen, Badges und Chat-Animation.

| Schrift | Seltenheit | Preis | Look |
|---|---|---|---|
| Default | Starter | 0 | normale Minecraft-Schrift, gehört jedem, bedeutet "keine Schrift" |
| Pixel Classic | Common | 30 | breite, eckige Pixel-Blöcke |
| Rounded | Common | 45 | dicke Linien mit runden Enden |
| Bold Block | Uncommon | 90 | schwer und breit |
| Thin Line | Uncommon | 120 | eine feine Linie (am besten ab GUI-Skala 2) |
| Typewriter | Uncommon | 150 | Serifen, alle Zeichen gleich breit |
| Gothic | Rare | 240 | breite Feder, gebrochene Bögen, Fraktur-Stil |
| Script | Rare | 280 | geneigte Schreibschrift mit kleinen Ausläufen |
| Retro Arcade | Rare | 320 | breite Blöcke mit Bildröhren-Streifen |
| Cyber | Rare | 380 | eckig, in der Mitte durchgeschnitten |
| Neon Tube | Epic | 600 | heller Kern mit dunklerer Leucht-Kontur |
| Graffiti | Epic | 780 | fette Sprühbuchstaben, die tanzen und manchmal tropfen |
| Runic | Epic | 950 | nur gerade, geritzte Striche |
| Royal | Legendary | 1600 | Serifen, kleine Krone auf Großbuchstaben |
| Glitch | Legendary | 2100 | versetzte Scheiben und ein blasser Doppelgänger |
| Cosmic | Legendary | 2600 | hohle Sternenstaub-Buchstaben mit kleinen Sternen |

- **Kaufen:** Der Goon Shop hat oben jetzt die Tabs `Hourly items` und `Fonts`. Schriften sind dauerhaft im Tab `Fonts` zu haben und
  kommen nicht in die stündliche Rotation (die bleibt dadurch für alle Versionen gleich). Kauf mit Bestätigung, Doppelkauf-Schutz,
  Speicherung in `wallet.json` wie bei allen Items. Alte `wallet.json`-Dateien laden ohne Verlust.
- **Ausrüsten:** Inventar, Tab `Fonts`, oder `Goon Cosmetics > Settings > Fonts`. Nicht gekaufte Schriften stehen dort als `Locked` und
  lassen sich nicht wählen. Auch Outfits merken sich die Schrift; ältere Outfits lassen sie unverändert.
- **Vorschau:** Karten zeigen deinen Namen in der Schrift mit dem ausgerüsteten Nametag-Stil. Der Detailbereich zeigt zusätzlich einen
  Chat-Satz und eine Tab-Zeile.
- **Einstellungen:** `Font in chat`, `Font in nametag`, `Font in tab list` (je an/aus, Standard an) in `Goon Cosmetics > Settings > Fonts` und
  im Inventar. Dazu `Show other players' fonts` bei den Ansichts-Einstellungen. Die Schalter gelten für alles, was DU siehst.
- **Abgedeckte Zeichen:** A-Z, a-z, 0-9, `_`, `-`, Leerzeichen. Alles andere (`ä`, `[`, `★` ...) kommt über den Verweis auf `minecraft:default`
  aus der Standard-Schrift, es entstehen keine Kästchen.
- **Breiten:** Nametag-Band, Badge-Position, Chat-Umbruch und Tab-Liste rechnet Minecraft selbst über die Font-Metriken. Schriften sind
  breiter als Standard (`xX_Steve-99`: 64 Pixel Standard, 73 bis 106 Pixel je Schrift), die Tab-Liste wird dadurch breiter.
- **Grenzen:**
  - Fremder Besitz lässt sich nicht prüfen, wie bei allen Items: Wer die Datei manipuliert, kann bei anderen jede bekannte Schrift zeigen.
  - Fremde Spieler zeigen nur Schriften, die dieser Client kennt; unbekannte Ids werden still zur Standard-Schrift.
  - Bei GUI-Skala 1 werden die 2-fach aufgelösten Zeichen grob, feine Details (Thin Line, Cosmic) können verschwinden.
  - Badge-Text und das GoonClient-Symbol behalten ihre Schrift, nur der Name ändert sich.
  - Eine eigene Schrift für das GoonClient-Menü ist nicht enthalten (optional im Auftrag, bewusst weggelassen).
- **Defekte Dateien:** Fehlt eine Datei oder ist sie kaputt, gilt die Standard-Schrift. Es gibt einen Eintrag im Log und einen roten Hinweis
  in `Goon Cosmetics > Settings > Fonts`. Geprüft wird beim ersten Benutzen und danach höchstens alle 30 Sekunden.
- **Lizenz:** Alle Schriften sind selbst erstellt: `tools/GenerateFonts.java` zeichnet jeden Buchstaben aus eigenen Linienzügen. Es steckt keine
  fremde Schriftdatei darin, deshalb gibt es keine fremden Lizenztexte. Der Rückfall nutzt die im Spiel vorhandene Minecraft-Schrift.

**Schriften neu erzeugen** (nach `gradlew clientClasses`, schreibt `assets/goonclient/font/*.json` und `textures/font/*.png`; Kontaktbögen:
`build/font_sheet.png`, `build/font_sheet_big.png`):

```
javac -encoding UTF-8 -cp build\classes\java\client -d build\tools tools\GenerateFonts.java
java -cp "build\tools;build\classes\java\client" GenerateFonts
```

**Tests:** `tools/FontLogicTest.java` (Katalog, Preisbänder, Kauf, Ids, Zeichenabdeckung, Alt-Daten, Atlas-Konsistenz),
`tools/BackendIntegrationTest.java` und `tools/backend/test_backend.py` (Rundlauf, ungültige Ids, Alt-Daten).

**Protokoll:** `cosmetics_v7` (Protokoll 7, neues Feld `font`). Alte Clients bekommen die neuen Pakete nicht. Einträge ohne `font` gelten als Standard-Schrift.

**Hochladen:** `tools/backend/server.py` im Repo `Goonboss1967/goonclient-backend` ersetzen und den Ordner `tools/backend/site` hochladen, danach
"Manual Deploy" auf Render. Ohne die neue `server.py` verwirft das Backend das Feld `font`: Andere Spieler sehen deine Schrift dann nicht,
auf Servern ohne GoonClient-Relay also gar nicht. Du selbst siehst sie trotzdem, Kauf und Ausrüsten funktionieren.

## Update 3.60.0: Haustiere komplett überarbeitet

Alle acht Haustiere (Kitten, Frog, Penguin, Bee, Fox, Bat, Little Ghost, Baby Dragon) sind neu gebaut: Chibi-Modelle aus vielen
kleinen Teilen, eigene Pixel-Art-Texturen und Animationen, die auf den Spieler reagieren.

- **Modelle und Texturen:** `cosmetics/pet/PetModels` beschreibt die Modelle als reine Daten. `tools/GeneratePets.java` malt die
  Texturen (`textures/pet/<id>.png`) und eine Kontaktübersicht (`build/pet_textures.png`). Nach einer Modelländerung neu erzeugen.
- **Animation:** Atmen, Blinzeln in unregelmäßigen Abständen und zufällige Idle-Aktionen. Bodentiere folgen dem Spieler federnd
  und bleiben auf dem Gelände, der Frosch hüpft, Flieger ziehen eine 8er-Bahn, neigen sich in Kurven und schwingen beim Stoppen nach.
- **Reaktionen:** Der Kopf schaut zum Spieler. Das Tier hüpft beim Sprung mit, duckt sich beim Schleichen und erschrickt bei Schaden.
- **Streicheln:** `/pet` oder die Taste `Pet key` im Pet-Cosmetic: Hüpfer, Augen zu, Herzchen. Das sieht nur der Streichelnde selbst.
- **Platz:** Tiere bleiben neben oder hinter dem Spieler und in der Ego-Ansicht weiter außen. Sie weichen Wänden aus und kommen ab
  10 Blöcken Abstand mit einem kleinen Teleport-Effekt zurück.
- **Änderung:** Es gibt keine Schulter-Tiere mehr. Die früheren Schulter-Tiere laufen jetzt neben dem Spieler her. Die Texte im Shop
  sagen "Walking pet" oder "Flying pet".
- **Einstellungen im Pet-Cosmetic:** `Size` (50-200 %), `Animation` (0-150 %), `Effects`, `Visible to others`, `Pet key`. Sie gelten
  für das gewählte Tier, nicht je Tier. Alte Configs laden weiter (Standardwerte für die neuen Felder).
- **Leistung:** Teile werden einmal vorberechnet, die Animation arbeitet auf wiederverwendeten Objekten. Ab 32 Blöcken läuft eine
  einfachere Animation ohne Partikel, ab 64 Blöcken wird nichts mehr gezeichnet.
- **Vorschau:** Shop und Inventar zeigen das Tier lebendig neben dem Spieler.
- **Tests:** `tools/PetAnimatorTest.java` prüft Winkel, NaN, stetige Übergänge, Federung, Abstand beim Dauerlauf, Teleport, Gelände
  und alte Configs.

**Fehler aus 3.59.0 behoben:** Der Kanal `cosmetics_v5` hatte neue Felder ohne neue Kennung bekommen. Jetzt gilt `cosmetics_v6`
(Protokoll 6, neues Feld `petStyle`). `Visible to others` wirkte erst nach einer weiteren Änderung, jetzt sofort.

**Hochladen:** `tools/backend/server.py` (speichert `petStyle`) und den Ordner `tools/backend/site`, danach "Manual Deploy" auf Render.

## Update 3.59.0: Auren komplett überarbeitet

Alle sieben Auren sind neu gebaut: weiche, leuchtende Teilchen statt harter Quadrate, erkennbare Formen, Schichten
(ruhiger Mantel, klare Form, wenige helle Funken) und Bewegung, die auf den Spieler reagiert.

- **Love:** kleine Herzen in zwei Größen steigen in einer langsamen Doppelhelix auf und wiegen seitlich; rosa Glimmer am
  Körper; ab und zu pulsiert ein großes Herz. Verlauf Pink → Rosé → Weiß.
- **Frost:** sechsstrahlige Schneekristalle in drei Größen schweben drehend herab, kalter Nebel kreist um die Füße,
  funkelnde Lichtpunkte; beim Laufen eine kurze Eisspur.
- **Matrix:** dichte Datenströme aus 0/1-Zeichen in einem Zylinder um den Körper, heller Kopf, verblassender Schweif,
  verschiedene Geschwindigkeiten, ab und zu ein Glitch mit versetzten Zeichen.
- **Flame:** echte Flammenzungen: breiter, heller Kern unten, spitz und kühler nach oben (Weiß-Gelb → Orange → Rot →
  Dunkelrot), unregelmäßiges Flackern, aufsteigende Funken, Glut am Boden, etwas Rauch.
- **Lightning:** zackige, verzweigte Blitzbögen (Mittelpunkt-Verschiebung) mit hellem Kern, cyanfarbenem Glow, kurzen
  Entladungen mit Nachleuchten und Funken; Gelb als Akzent.
- **Golden Rings:** vier dünne Ringe in verschiedenen Höhen kreisen gegenläufig, leicht geneigt und auf und ab wandernd,
  mit mitlaufendem Glitzer; regelmäßig leuchtet ein Ring auf und schickt eine goldene Welle nach oben.
- **Void:** dunkler Sog: violette und fast schwarze Teilchen werden spiralförmig zum Körper gezogen, helle Sterne im
  Inneren, ab und zu ein violett-magentafarbener Riss mit Welle am Boden.

**Reaktion auf den Spieler:** im Stehen ruhig und "atmend", beim Laufen bleibt die Aura als Sog hinter dir, beim Sprinten
intensiver, beim Springen ein kurzer Impuls nach außen, beim Schleichen gedämpft. Übergänge sind weich geglättet.

**Neue Einstellungen** (Goon Cosmetics → Aura): **Intensity** (Dichte, 25–200 %), **Size** (50–200 %), **Speed**
(25–200 %), **Custom colors** mit **Color 1** und **Color 2**, **Visible to others** (aus = nur du siehst deine Aura).
Andere Spieler sehen deine Aura mit deinen Einstellungen. Alte Configs laden ohne Änderung (fehlende Werte = Standard).

**Vorschau:** Shop und Inventar zeigen die Aura animiert an deinem Spieler, mit deinen aktuellen Einstellungen.

**Technik und Grenzen:**
- Die Berechnung steckt in `cosmetics/aura/AuraEngine` (reines Java, ohne Minecraft, getestet in `tools/AuraEngineTest.java`):
  jedes Teilchen folgt direkt aus Zeit und Seed, deshalb kein Aufploppen, keine Allokationen pro Bild und bei gleichem Seed
  exakt dasselbe Bild. Gezeichnet wird in `AuraRenderer` als zur Kamera gedrehte Sprites aus `textures/aura/atlas.png`
  (Generator: `tools/GenerateAuraAtlas.java`).
- Höchstens **70 Teilchen** pro Aura und Spieler. Detailstufe nach Entfernung: bis 16 Blöcke voll, bei 32 Blöcken etwa
  20 %, ab 64 Blöcken nichts.
- Leuchtende Teilchen werden **additiv** gezeichnet (eigene Render-Pipeline nach dem Vorbild von Minecrafts "eyes"),
  dunkle Teilchen und Rauch normal überblendet. Lässt sich die Pipeline nicht anlegen, wird automatisch "eyes" benutzt.
- Die Einstellungen gelten für die gewählte Aura (eine gemeinsame Einstellung für alle Auren, nicht je Aura getrennt).
- Server: neue Felder `auraStyle`, `auraColor1`, `auraColor2` (dafür `server.py` hochladen).

## Update 3.58.0: Auren

- **Neue Cosmetic-Art: Auren.** Eigene Kategorie "Auras" im Goon Shop und im Inventar. Eine Aura umgibt den **ganzen
  Körper** vom Kopf bis zu den Füßen (nicht nur den Kopf wie Accessoires) und kippt beim Schleichen nicht mit.
  - **Love Aura** (Uncommon): rosa Herzen steigen langsam am Körper hoch.
  - **Frost Aura** (Rare): Schneeflocken steigen auf, an den Füßen dreht sich ein Eisring.
  - **Matrix Aura** (Rare): grüne Code-Streifen rasen am Körper hoch.
  - **Flame Aura** (Epic): Flammen lodern aus glühender Glut an den Füßen nach oben.
  - **Lightning Aura** (Epic): zuckende Blitze kreisen um den ganzen Körper.
  - **Golden Rings** (Legendary): drei goldene Ringe drehen sich an Füßen, Hüfte und Kopf und wippen leicht.
  - **Void Aura** (Legendary): violette Teilchen wirbeln in einer Spirale nach oben.
- Auren lassen sich mit Hut, Flügeln, Accessoire und Haustier kombinieren, gehören zu den Outfits und stehen in den
  Freundes-Stats. Andere GoonClient-Spieler sehen deine Aura (Ausblenden mit "Show other players' accessories").
- Server: neues Feld `aura` (dafür `server.py` hochladen). Das Server-Relay nutzt jetzt den Kanal `cosmetics_v5`.

## Update 3.57.0: Goon Shop und Haustiere

- **Der Hourly Shop heißt jetzt wieder "Goon Shop"** (Tab, Banner, Meldungen, Missionen, Website). Er funktioniert wie
  bisher: jede volle Stunde 8 neue Items.
- **Neue Cosmetic-Art: Haustiere (Pets).** Eigene Kategorie "Pets" im Goon Shop und im Inventar, ein Haustier gleichzeitig.
  - **Schulter-Haustiere** sitzen auf deiner linken Schulter und bewegen sich mit dir:
    **Kitten** (Common), **Frog** (Uncommon), **Penguin** (Uncommon), **Fox** (Rare).
  - **Fliegende Haustiere** schweben neben deinem Kopf, wippen auf und ab und schlagen mit den Flügeln:
    **Bee** (Uncommon), **Bat** (Rare, rote Augen), **Little Ghost** (Epic, leuchtet), **Baby Dragon** (Legendary,
    goldene Hörner, leuchtende Flügelspitzen).
  - In der Beschreibung steht jeweils "Shoulder pet" oder "Flying pet". Die Vorschau zeigt das Haustier an deinem Spieler.
  - Andere GoonClient-Spieler sehen dein Haustier (über den GoonClient-Server und Server mit GoonClient). Ausblenden mit
    "Show other players' accessories". Haustiere gehören auch zu den Outfits und stehen in den Freundes-Stats.
- Server: neues Feld `pet` (dafür `server.py` hochladen). Das Server-Relay nutzt jetzt den Kanal `cosmetics_v4`; Spieler mit
  älteren Versionen sehen sich über den GoonClient-Server weiterhin, nur nicht ihre Haustiere.

## Update 3.56.0: Exklusive Items per Code – Hacker Orbit

- **Neue Seltenheit "Exclusive"** (pink): Items, die es **nur über einen Redeem-Code** gibt. Sie kommen nie in den
  Hourly Shop, lassen sich nicht kaufen, nicht verschenken und nicht auf die Wunschliste setzen. Jedes Item, das es
  künftig per Code gibt, ist exklusiv. Im Inventar steht bei ihnen "Exclusive item - only from a redeem code".
- **Hacker Orbit** (Accessoire, Exclusive): leuchtend grüne Code-Zeichen (0, 1, <, >, /, #) kreisen in zwei Höhen um
  den Kopf, dazwischen kleine Datenpunkte. Jeder Pixel flackert einzeln wie auf einem Terminal. Das Gesicht bleibt frei.
- **Codes können Items geben:** In `codes.json` gibt ein Eintrag mit `"item": "accessory.hackerorbit"` das Item
  zusätzlich (Coins dürfen dann 0 sein). Neuer Code: `py -3 tools/backend/add_code.py 0 --item accessory.hackerorbit`.
  Das Item muss im Client als exklusives Item eingebaut sein.
  - Clients vor 3.56.0 können solche Codes nicht einlösen (der Server antwortet "update GoonClient"), damit niemand
    den Code verbraucht, ohne das Item zu bekommen.
  - Wie bei Coins gilt jeder Code pro Konto nur einmal, und das Item ist gegen Bearbeiten der Datei geschützt.
- Server: `server.py` und `codes.json` hochladen.

## Update 3.55.0: Pack Mixer – Wind Charges

- Neues Abteil **Wind Charges** im Pack Mixer (unter "Ender Pearls"), mit Vanilla und allen Pack-Varianten:
  - **Wind Charge:** das Item zusammen mit der fliegenden Kugel (`entity/projectiles/wind_charge`); wer die Wind Charge aus
    einem Pack wählt, bekommt beides.
  - **Wind Burst:** der Windstoß beim Aufprall (alle Bilder von `particle/gust_*` und `particle/small_gust_*`) als ein Paket.

## Update 3.54.0: Namensschilder in der Tab-Liste und GoonClient-Symbol

- **Tab-Liste:** Animierte Namensschilder und Badges von GoonClient-Spielern erscheinen jetzt auch in der Tab-Liste,
  genau wie über dem Kopf.
- **GoonClient-Symbol:** Jeder, der gerade mit GoonClient spielt, hat vor seinem Namen und vor seiner Badge ein kleines
  lila GoonClient-"G", über dem Kopf und in der Tab-Liste, auch ohne gekaufte Cosmetics. Ausschalten:
  Goon Cosmetics → "What I see from other players" → **"GoonClient icon"**.
- **Rang bleibt:** Animiert wird nur noch der Spielername selbst. Rang, Farben und Zusätze des Servers (z.B. "VIP" davor,
  Clan dahinter) bleiben unverändert; Symbol und Badge stehen direkt vor dem Namen: `VIP [G] BOSS Name blubby`.
- Spieler außerhalb der Sichtweite werden für die Tab-Liste beim GoonClient-Server nachgefragt (alle 60 Sekunden).
- Server: `/v1/cosmetics` meldet zusätzlich, wer in den letzten 15 Minuten online war (`"active"`); nur diese Spieler
  bekommen das Symbol. Dafür `server.py` hochladen. Mit der alten `server.py` bekommt jeder mit Eintrag das Symbol.

## Update 3.53.1: Freunde-Modul repariert

- **Fix: Freunde wurden auf vielen Servern nicht hervorgehoben** (kein Stern, keine Freundesfarbe über dem Kopf, in der
  Tab-Liste und im Chat, Freund nie "online"). Ursache: Freunde wurden nur über ihre Mojang-UUID erkannt. Offline-Server
  und manche Proxys geben Spielern aber eine eigene UUID, dort passte sie nie. Jetzt zählt zusätzlich der Name, wenn die
  UUID nicht passt.
- **Fix: "Right-click in chat" ging nicht.** Der Rechtsklick hing an einer Methode, die es seit Minecraft 1.21.11 nicht mehr
  gibt. Jetzt wird beim Rechtsklick im offenen Chat der Name unter der Maus gesucht (wie beim Linksklick von Minecraft)
  und der Spieler hinzugefügt.
- Geprüft im Spiel: Freund mit abweichender UUID bekommt Stern und Farbe über dem Kopf und in der Tab-Liste und gilt als
  online, sein Name im Chat ist markiert, Rechtsklick auf einen Namen im Chat fügt ihn hinzu.

## Update 3.53.0: Download-Bereich und Updater nach Minecraft-Version

- **Website:** Neuer Abschnitt **Download** mit einer Karte pro verfügbarer Minecraft-Version (Version, Größe,
  Download-Knopf). Alle Download-Knöpfe der Seite springen dorthin. Aktuell gibt es **Minecraft 1.21.11**.
- **Updater:** Der Client sagt dem Server jetzt, für welche Minecraft-Version er läuft, und bekommt nur Updates für genau
  diese Version. Ältere Clients bekommen wie bisher die 1.21.11-Version.

## Update 3.52.1: Fix "7b" vor Namen mit animiertem Nametag

- **Fix:** Bei manchen Spielern standen mit animiertem Nametag fremde Zeichen vor dem Namen, z.B. "7b533m" statt "533m".
  Ursache: Einige Server schreiben alte Minecraft-Farbcodes direkt in den Namen (z.B. "§7§b533m"). Das Nametag färbt den
  Namen Buchstabe für Buchstabe ein; dabei stand das "§" allein und der Buchstabe dahinter (7, b ...) wurde sichtbar.
- Jetzt werden diese Codes vor dem Einfärben entfernt (auch Hex-Farben und Fett/Kursiv-Codes). Das animierte Nametag
  ersetzt die Farben des Servers ohnehin. Geprüft mit "§7§b533m" → "533m", "§7543m" → "543m" und weiteren Fällen.
- Betrifft Nametags über dem Kopf, in der Tab-Liste und im Chat. Spieler sehen den Fix, sobald **sie selbst** (die den Namen
  anzeigen) 3.52.1 haben.

## Update 3.52.0: Daily Missions und 8 Items im Hourly Shop

- **Daily Missions** (Tab "Missions", zwischen täglicher Belohnung und den Missionen): jeden Tag **3 neue Aufgaben**,
  für alle Spieler gleich, z.B. "Play for 30 minutes today", "Play 3 emotes today", "Buy an item in the Hourly Shop",
  "Claim your daily reward", "Earn 100 coins by playing today" oder "Claim a Battle Pass reward". Nie zwei Aufgaben
  derselben Art an einem Tag.
  - Jede Aufgabe gibt beim Abholen **Goon Coins (50–300) und Battle-Pass-XP (100–400)**.
  - Fortschrittsbalken, "Claim"-Knopf und Countdown bis zu den neuen Aufgaben um Mitternacht. Erledigte Aufgaben werden
    im Spiel gemeldet. Der Fortschritt zählt nur für den jeweiligen Tag.
  - Wie die Coins gegen Bearbeiten der Datei geschützt.
- **Missionen geben Battle-Pass-XP:** wie bisher +250 XP pro abgeholter Mission; das steht jetzt auch in der Liste und in
  der Meldung beim Abholen.
- **Hourly Shop: 8 statt 5 Items pro Stunde.** In breiten Fenstern alle in einer Reihe, sonst in zwei Reihen zu 4.

## Update 3.51.2: Pack Mixer – Varianten scrollen

- **Fix:** Mit vielen Texture Packs verschwanden im Pack Mixer Varianten: Der Inspector zeigte nur so viele Kacheln, wie
  unten Platz hatten; alle weiteren Packs waren nicht erreichbar. Außerdem wurde die große Vorschau mit jeder Zeile kleiner.
- Die Varianten-Kacheln im Inspector lassen sich jetzt mit dem **Mausrad scrollen** (rechts zeigt eine schmale Leiste die
  Position, unten steht z.B. "30 packs - scroll for more"). Die große Vorschau bleibt dabei groß. Beim Wechsel zu einem
  anderen Teil beginnt die Liste wieder oben.
- Geprüft im Spiel mit 30 Packs, die alle das Diamantschwert ändern: alle 31 Varianten (Vanilla + 30) sind erreichbar.

## Update 3.51.1: Item Scale nur für Items auf dem Boden

- **Fix:** Eine eigene Größe für den End-Kristall in der Item-Liste von **Item Scale** hat auch **platzierte** End-Kristalle
  (die Entity) riesig gemacht. Die Item-Liste gilt jetzt nur noch für **gedroppte Items** auf dem Boden; platzierte
  Kristalle, Blöcke und andere Entities bleiben normal groß. In der Liste steht das als Hinweis unter dem Regler.

## Update 3.51.0: Theme "Monochrome"

- **Neues Theme "Monochrome"** (Goon Cosmetics → Themes): Schwarz, Grau und Weiß ohne Farbakzent, passend zur Website.
  Hintergrund fast schwarz, Flächen in dunklem Grau, Auswahl und Hervorhebungen in hellem Grau/Weiß.
- Auf dem hellen Akzent werden Schalter-Knöpfe und das "G" im Logo automatisch dunkel gezeichnet, damit sie sichtbar
  bleiben (die anderen Themes sehen aus wie bisher).

## Update 3.50.1: Update-Fenster kommt zuverlässig

- **Fix:** Das Update-Fenster ("Neues Update verfügbar!" mit "Jetzt herunterladen" / "Später") kam oft nicht. Ursache:
  Der Client fragte nur einmal beim Spielstart nach einem Update. Schlug diese Abfrage fehl (z.B. weil der Server auf
  Render gerade aufwacht oder neu deployt wird), wurde erst nach 3 Stunden wieder gefragt. Außerdem prüfte das Fenster
  nur im allerersten Moment beim Öffnen des Menüs.
- Jetzt fragt der Client **bei jedem Öffnen des GoonClient-Menüs** (Öffnungstaste) nach einem Update (höchstens alle
  30 Sekunden), nach einem Fehler außerdem automatisch alle 2 Minuten. Kommt die Antwort erst, während das Menü schon
  offen ist, erscheint das Fenster sofort. "Später" blendet es bis zum nächsten Spielstart aus.

## Update 3.50.0: Battle Pass mit eigenem Tab und seitlich scrollender Leiste

- **Battle Pass statt Monats-Season-Pass:** Die Season wechselt nicht mehr automatisch jeden Monat, sondern läuft, bis
  eine neue Season eingebaut wird (kein Enddatum). Aktuell: **Season 1: Neon Nights** mit allen 7 limitierten Cosmetics
  (Volt, Circuit, Robot, Data Cubes, Cyber Helmet, Circuit Wings, Synthwave). Free- und Premium-Track (1000 Coins)
  bleiben wie in 3.49.
- **Eigener Tab "Battle Pass"** in der Seitenleiste, unter dem Event-Shop und über "Missions" (dort ist der Pass nicht
  mehr).
- **Seitlich scrollende Leiste statt Tabelle:** Alle 30 Stufen nebeneinander, oben die Free-Belohnung, unten die
  Premium-Belohnung, dazwischen die Stufen-Leiste mit dem Fortschritt. Items mit Live-Vorschau, Coins mit Münze.
  Scrollen mit dem Mausrad, den Pfeilen oder der Leiste darunter; beim Öffnen springt sie zur aktuellen Stufe.
  Abholbare Belohnungen leuchten ("CLAIM"), Klick = abholen. Unten zeigt ein Detailbereich die angeklickte Belohnung groß.
- Wer im alten Monats-Pass schon XP oder Premium hatte, behält beides in Season 1; Stufen, die jetzt ein Item geben,
  können noch einmal abgeholt werden.
- Neue Season: Bescheid sagen, dann wird sie mit neuen Cosmetics als Season 2 eingebaut (Client-Update).

## Update 3.49.1: Season-Pass zeigt die nächste Season

- Hat die laufende Season keine eigenen Cosmetics (z.B. Oktober 2026), zeigt der Season-Pass unten die Cosmetics der
  **nächsten** Season als Vorschau ("Coming next season: November 2026 - Neon Nights", Karten mit "Soon").
- In den **letzten 24 Stunden** einer Season kann man Premium nicht mehr kaufen ("Premium closed"), damit niemand
  1000 Coins für ein paar Stunden Premium bezahlt. Premium der neuen Season gibt es ab ihrem Start.

## Update 3.49.0: Free und Premium Season-Pass mit limitierten Season-Cosmetics

- **Zwei Tracks:** Jede der 30 Stufen hat jetzt eine **Free**-Belohnung (obere Reihe) und eine **Premium**-Belohnung
  (untere Reihe, mit Goldrand). Den **Premium-Pass** kauft man im Season-Pass für **1000 Goon Coins** pro Season
  (zweiter Klick bestätigt). Schon erreichte Stufen können danach sofort auch premium abgeholt werden; XP und
  Free-Belohnungen bleiben. Mit der nächsten Season läuft Premium ab, gewonnene Items bleiben für immer.
- **Premium gibt mehr:** mehr Cosmetics (5 statt 2) und mehr Coins (Premium-Coins: 165 bis 585 pro Stufe,
  Stufe 10/20 sogar 1500/3000, zusammen gut 13.000 extra).
- **Limitierte Season-Cosmetics "Neon Nights" (Season November 2026),** nur im Season-Pass, nie im Shop, nicht
  verschenkbar:
  - Free: **Volt** Badge (Stufe 8, flackerndes Neon-Schild "⚡VOLT"), **Circuit** Nametag (Stufe 20, Datenpakete rasen
    durch den Namen).
  - Premium: **Robot** Emote (Stufe 6), **Data Cubes** (Stufe 12, vier leuchtende Würfel kreisen um den Kopf),
    **Cyber Helmet** (Stufe 18, Helm mit Cyan-Visier und Antenne), **Circuit Wings** (Stufe 24, Platinen mit leuchtenden
    Leiterbahnen), **Synthwave** Cape (Stufe 30, Legendary, animiert: gestreifte Sonne über einem Neon-Gitter).
  - Unter den Stufen zeigt der Season-Pass alle Season-Cosmetics mit Vorschau; im Inventar steht bei ihnen, aus welcher
    Season und Stufe sie stammen.
- Seasons ohne eigene Cosmetics geben auf diesen Stufen Coins. Neue Season-Cosmetics für spätere Monate brauchen ein
  Client-Update (die Designs sind eingebaut).
- Premium-Stand und Premium-Belohnungen sind wie die Coins gegen Bearbeiten der Datei geschützt.
- Server: das neue Emote "Robot" ist freigeschaltet (dafür `server.py` hochladen).

## Update 3.48.0: Wunschliste, Outfits, Season-Pass und Geschenke

- **Wunschliste:** Im Inventar zeigt der neue Schalter **"Show locked"** auch Items, die dir noch nicht gehören
  (abgedunkelt, mit Preis und "In shop", wenn sie gerade im Hourly Shop sind). Mit **"Add to wishlist"** markierst du sie
  (Herz). Taucht ein markiertes Item im Hourly Shop auf, gibt es eine Meldung (oben im Bild und im Chat), einmal pro Stunde.
- **Outfits:** Oben im Inventar speicherst du deinen aktuellen Look (Cape, Hut, Flügel, Accessoire, Nametag, Badge) unter
  einem Namen, bis zu 8 Outfits. Anklicken und **"Wear"** zieht alles mit einem Klick an; leere Plätze werden abgelegt,
  Items, die dir nicht (mehr) gehören, übersprungen. "Save current look" aktualisiert ein Outfit, "Delete" löscht es.
- **Season-Pass (kostenlos):** Jeden Monat eine neue Season mit **30 Stufen**, zu sehen im Tab "Missions".
  XP gibt es für aktive Spielzeit (+10 pro Minute), die tägliche Belohnung (+100) und jede abgeholte Mission (+250);
  alle 500 XP eine Stufe (volle Season etwa 25 Stunden). Jede Stufe gibt Goon Coins: meist 110 bis 290, jede 5. Stufe 500,
  Stufe 10/20/30 sogar 1000/2000/3000 (zusammen 13.500 pro Season). Leuchtende Stufe anklicken = abholen. Am Monatsende
  beginnt die nächste Season bei 0, nicht abgeholte Belohnungen verfallen.
- **Geschenke an Freunde:** In den Stats eines bestätigten Freundes (Friends-Tab, "Stats") gibt es "Send a gift":
  100, 500, 1000 oder 5000 Goon Coins oder ein Item aus dem aktuellen Hourly Shop, das der Freund noch nicht hat
  (du zahlst den Preis). Zweiter Klick bestätigt.
  - Zustellung über den Server, auch wenn der Freund gerade offline ist; er bekommt eine Meldung, sobald er online ist,
    und du eine, wenn er es erhalten hat.
  - Ein Server-Neustart kann kein Geschenk verlieren: Dein Client schickt es erneut, bis der Freund es hat, und sein
    Client schreibt jedes Geschenk nur einmal gut. Hat der Freund das Item inzwischen, bekommt er dessen Preis als Coins.
  - Beide brauchen 3.48.0. Höchstens 20 Geschenke gleichzeitig unterwegs.
- Season-Stand, verschickte und empfangene Geschenke sind wie die Coins gegen Bearbeiten der Datei geschützt.
- Server: neue Routen `/v1/gifts`, `/v1/gifts/send`, `/v1/gifts/claim` (dafür `server.py` hochladen).

## Update 3.47.0: Freunde gehen nicht mehr verloren, Update-Fenster

- **Fix: Freunde verschwanden und mussten neu angefragt werden.** Ursache: Der Server läuft auf Render im Gratis-Plan,
  dort wird die Datenbank-Datei bei **jedem Neustart gelöscht** (nach jedem Deploy und wenn Render den schlafenden Server
  wieder aufweckt). Damit waren alle Freundschaften und offenen Anfragen weg.
- **Jetzt stellt der Client Freundschaften selbst wieder her:** Jeder Client kennt seine Freundesliste lokal. Fehlt ein
  Freund beim Server, schickt der Client still eine neue Anfrage; kommt eine Anfrage von jemandem, der schon in der
  eigenen Freundesliste steht, wird sie still angenommen. Sobald beide einmal online waren, seid ihr automatisch wieder
  Freunde, ohne Klicken und ohne Chat-Meldungen. Fremde Anfragen werden nie automatisch angenommen.
  - Pro Freund höchstens eine automatische Anfrage pro Spielstart (geht die Freundschaft mitten im Spiel erneut verloren,
    wird erneut angefragt). Wer einen Freund wirklich loswerden will, entfernt ihn aus der Liste.
  - Damit es greift, brauchen **beide** Spieler Version 3.47.0. Freundschaften, die schon verloren sind, kommen so auch
    zurück, solange der Freund noch in der lokalen Liste steht.
- **Update-Fenster:** Gibt es eine neue Version, erscheint beim Öffnen des GoonClient-Menüs ein Fenster mit Version und
  den wichtigsten Neuerungen und zwei Knöpfen: **"Jetzt herunterladen"** (lädt und prüft das Update sofort, mit
  Fortschrittsbalken; installiert wird beim Schließen von Minecraft) und **"Später"** (oder Esc; das Fenster kommt beim
  nächsten Spielstart wieder). Das gilt ab dem **nächsten** Update nach 3.47.0.

## Update 3.46.0: Event-System, tägliche Belohnung und Missionen

- **Event-System statt fest eingebautem Halloween:** Event-Shops (Name, Start, Ende, Währung, Coins pro Minute, Farbe,
  Aussehen, Items) kommen jetzt aus `tools/backend/events.json`. Neue Termine, Verlängerungen oder ein neues Event mit
  schon eingebauten Items brauchen **keine neue Client-Version**: Datei ändern, hochladen, fertig (gilt sofort, ohne
  Neustart; der Client fragt alle 30 Minuten nach und merkt sich die Liste für Spielen ohne Verbindung).
  - Mehrere Events gleichzeitig möglich, jedes mit eigenem Tab "<Name> Shop", eigenem Banner im Hourly Shop und eigener,
    geschützter Währung. Aussehen: `"theme": "halloween"` (Kürbis, Fledermäuse), `"winter"` (Schnee) oder `"default"`.
  - Zeiten mit Zeitzone angeben, z.B. `"start": "2026-12-20T00:00:00+01:00"`. Ein Event dauert höchstens 62 Tage.
  - Neue Event-Items selbst (Designs) brauchen weiterhin ein Client-Update; Items, die der Client nicht kennt, ignoriert er.
  - Das Halloween-Event läuft genau wie bisher (bis 7.11.2026), Halloween Coins und gekaufte Items bleiben erhalten.
- **Tägliche Belohnung mit Login-Streak:** einmal pro Tag Goon Coins abholen: Tag 1 bis 7 gibt 50, 75, 100, 150, 200,
  300 und **600** Coins, danach beginnt die Woche von vorn (die Streak zählt weiter). Wer einen Tag auslässt, fängt wieder
  bei Tag 1 an. Erinnerung beim Betreten einer Welt und ein Banner im Hourly Shop. Uhr zurückstellen bringt nichts.
- **Missionen und Erfolge:** 23 Ziele mit Coin-Belohnung, z.B. "Warming Up" (1 Stunde spielen, +100), "Collector"
  (10 Items, +400), "Dance Machine" (100 Emotes, +500), "Full Week" (7 Tage Streak, +500), "Money Printer" (Coin Upgrader
  voll, +2500), "No Life" (100 Stunden, +4000). Erreichte Missionen werden gemeldet und per Knopf abgeholt ("Claim all").
  Spielzeit, Käufe, Codes und Upgrades von früher zählen sofort mit.
- **Neuer Tab "Missions"** mit der Streak-Woche (7 Kacheln, Countdown bis Mitternacht) und allen Missionen mit
  Fortschrittsbalken; im Titel steht, wie viele Belohnungen bereitliegen.
- Streak, Emote-Zähler und abgeholte Missionen sind wie die Coins gegen Bearbeiten der Datei geschützt; alte Konten bleiben
  gültig.
- Server: neue Route `GET /v1/events` und neue Datei `events.json` (dafür `server.py` und `events.json` hochladen).

## Update 3.45.0: Limitierter Halloween Shop mit Halloween Coins

- **Neue limitierte Währung "Halloween Coins":** Während des Events gibt es pro Minute aktiver Spielzeit zusätzlich
  3 Halloween Coins (unabhängig vom Coin Upgrader, AFK zählt nicht). Sie sind wie die Goon Coins gegen Bearbeiten der Datei
  geschützt.
- **Neuer Tab "Halloween Shop"** (mit Kürbis-Icon, nur während des Events sichtbar): Halloween-Coins-Guthaben, ein
  **Countdown** (Tage, Stunden, Minuten, Sekunden) und das Ablaufdatum. Der Shop verschwindet am **7. November 2026 um
  00:00 Uhr** (deutsche Zeit). Im Hourly Shop führt ein Banner mit Restzeit direkt dorthin.
- **15 limitierte Items** (nur mit Halloween Coins, nie im Hourly Shop):
  - Hüte: Reaper Hood (dunkle Kapuze mit roten Augen), Jack-o'-Lantern (leuchtender geschnitzter Kürbis).
  - Flügel: Skeleton Wings (aus Knochen), Vampire Wings (rote Fledermausflügel mit leuchtenden Kanten).
  - Accessoires: Vampire Fangs, Spider Buddy (Spinne auf dem Kopf), Orbiting Ghosts (Legendary, drei kleine Geister kreisen).
  - Capes (animiert): Lantern (Kürbisgesicht mit flackernder Kerze), Haunted (Geister steigen durch die Nacht auf).
  - Badges: R.I.P. (pulsierend), BOO! (flackert orange und lila).
  - Nametags: Spooky (orange und lila, mit Flackern), Haunted (Buchstaben verblassen wie Geister).
  - Emotes: Zombie Walk, Boo! (zusammenkauern und hochspringen).
- Gekaufte Halloween-Items bleiben für immer im Inventar (dort mit "Limited Halloween 2026 item" markiert).
- Server: die zwei neuen Emotes sind freigeschaltet (dafür `server.py` neu hochladen).

## Update 3.44.0: 49 neue Shop-Items

- **8 neue Emotes** (schlicht und sauber animiert): Thumbs Up, Point, Shrug, Clap, Think, Facepalm, Bow, Cheer.
- **9 neue Capes:** Ash, Mint, Cherry, Toxic, Pumpkin, Glacier, dazu animiert Storm (Blitze), Lava und Nebula (Legendary).
- **10 neue Badges:** Check ✔, Music ♫, Snow ❄, Anchor ⚓, Peace ☮, Sword ⚔ und Infinity ∞ (pulsierend), Atom ⚛ und
  Comet ☄ (schimmernd), Galaxy ✺ (Regenbogen).
- **6 neue Nametags:** Candy (rollende Zuckerstangen-Streifen), Ocean (Wellen mit Schaum), Sunset, Matrix (flackernder Code),
  Lava (glühende Risse) und Hologram (Legendary, Scan-Licht).
- **6 neue Hüte:** Headband, Party Hat, Santa Hat, Witch Hat, Propeller Cap (der Propeller dreht sich) und Star Crown
  (Legendary, Regenbogen-Sterne kreisen um die Krone).
- **3 neue Flügel:** Butterfly Wings, Shadow Wings (violett leuchtende Kanten), Ice Wings (leuchtende Eiskristalle).
- **7 neue Accessoires:** Mustache, Bow Tie, Monocle, Bandana, Flower Crown, Spirit Wisps (schwebende Geister-Lichter) und
  Golden Aura (Legendary, ein Ring aus goldenem Licht).
- Alle neuen Items kommen ganz normal in den Hourly Shop (Seltenheit bestimmt, wie oft sie auftauchen).
- Server: die neuen Emotes sind freigeschaltet, damit andere Spieler sie sehen (dafür `server.py` neu hochladen).

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