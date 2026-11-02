from typing import Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import Journey, JourneyMilestone, UserJourneyProgress
from app.schemas import MilestoneUnlockCelebration, UserJourneyProgressResponse, JourneyResponse, JourneyMilestoneResponse
from app.services.metrics import calculate_journey_calories

DEFAULT_JOURNEYS = [
    {
        "slug": "lord-of-the-rings",
        "title": "Il Viaggio dell'Anello",
        "universe": "Terra di Mezzo",
        "description": "Dalle dolci colline della Contea fino alle fiamme voraci di Monte Fato. Un'epopea di 2.200 km su due ruote attraverso l'oscurità e la gloria.",
        "total_distance_km": 2200.0,
        "badge_icon": "ring",
        "milestones": [
            {"order_index": 0, "name": "Hobbiville & La Contea", "distance_km": 0.0, "lore_text": "Inizia il viaggio verso l'ignoto lasciandosi alle spalle l'erba verde e la tranquillità di Casa Baggins.", "badge_icon": "home"},
            {"order_index": 1, "name": "Brea & Il Puledro Impennato", "distance_km": 190.0, "lore_text": "L'incontro con Grampasso tra le ombre e la pioggia della locanda più famosa di Eriador.", "badge_icon": "beer"},
            {"order_index": 2, "name": "Colle Vento (Weathertop)", "distance_km": 350.0, "lore_text": "L'assalto notturno dei Cavalieri Neri e la ferita della lama Morgul sulla sommità dell'antica torre.", "badge_icon": "flame"},
            {"order_index": 3, "name": "I Guadi del Bruinen", "distance_km": 600.0, "lore_text": "Le acque furiose richiamate da Elrond spazzano via i nove destrieri neri.", "badge_icon": "waves"},
            {"order_index": 4, "name": "Gran Burrone (Rivendell)", "distance_km": 736.0, "lore_text": "L'Ultima Casa Accogliente ad est del Mare. Si tiene il Gran Consiglio e nasce la Compagnia dell'Anello.", "badge_icon": "castle"},
            {"order_index": 5, "name": "Il Passo di Caradhras", "distance_km": 950.0, "lore_text": "La crudele tempesta di neve e ghiaccio costringe la Compagnia a scendere verso le tenebre della montagna.", "badge_icon": "mountain-snow"},
            {"order_index": 6, "name": "Le Miniere di Moria", "distance_km": 1100.0, "lore_text": "'Tu non puoi passare!'. Il sacrificio di Gandalf contro il Flagello di Durin sul ponte di Khazad-dûm.", "badge_icon": "skull"},
            {"order_index": 7, "name": "I Boschi di Lothlórien", "distance_km": 1300.0, "lore_text": "La luce dorata degli alberi mallorn, lo specchio di Galadriel e i doni che salveranno il mondo.", "badge_icon": "trees"},
            {"order_index": 8, "name": "Cascate di Rauros & Amon Hen", "distance_km": 1500.0, "lore_text": "Il corno di Gondor suona per l'ultima volta. Boromir difende gli Hobbit; la Compagnia si divide.", "badge_icon": "shield-alert"},
            {"order_index": 9, "name": "Le Paludi Morte", "distance_km": 1700.0, "lore_text": "'Non seguire le luci!'. Volti spettrali di guerrieri caduti riposano sotto le acque limacciose.", "badge_icon": "ghost"},
            {"order_index": 10, "name": "Il Cancello Nero di Mordor", "distance_km": 1850.0, "lore_text": "I cancelli di ferro del Morannon sono invalicabili. Non resta che fidarsi della via segreta di Gollum.", "badge_icon": "door-closed"},
            {"order_index": 11, "name": "Il Valico di Cirith Ungol", "distance_km": 2000.0, "lore_text": "La tana dell'orrore a otto zampe: Shelob. La luce di Eärendil squarcia il buio più pesto.", "badge_icon": "spider"},
            {"order_index": 12, "name": "La Voragine di Monte Fato", "distance_km": 2200.0, "lore_text": "L'Unico Anello brucia e scompare nel magma. La Torre Oscura crolla: la Terra di Mezzo è libera!", "badge_icon": "trophy"},
        ]
    },
    {
        "slug": "elden-ring",
        "title": "Elden Ring: La Marcia del Senzaluce",
        "universe": "Interregno",
        "description": "L'avventura completa attraverso l'Interregno, comprensiva di backtracking obbligato tra superficie, profondità sotterranee e ritorno alla capitale distrutta.",
        "total_distance_km": 850.0,
        "badge_icon": "swords",
        "milestones": [
            {"order_index": 0, "name": "Primo Passo di Sepolcride", "distance_km": 0.0, "lore_text": "La Grazia dorata ti risveglia nella cappella dell'Attesa. Il sentiero verso il titolo di Lord Ancestrale comincia qui.", "badge_icon": "sparkles"},
            {"order_index": 1, "name": "Deviazione a Sud: Penisola del Pianto", "distance_km": 60.0, "lore_text": "Esplorazione verso sud per recuperare frammenti e semi dorati. Castello di Morne caduto nella follia.", "badge_icon": "compass"},
            {"order_index": 2, "name": "Backtracking a Nord: Castello di Grantempesta", "distance_km": 130.0, "lore_text": "Ritorno a nord attraverso le rovine del Colle Tempesta. Godrick l'Innestato cede la sua Runa Maggiore.", "badge_icon": "axe"},
            {"order_index": 3, "name": "Liurnia Lacustre & Accademia Raya Lucaria", "distance_km": 210.0, "lore_text": "Navigazione attraverso le nebbie dello stagno monumentale. Rennala protegge la Runa della Rinascita.", "badge_icon": "moon"},
            {"order_index": 4, "name": "Discesa Sotterranea: Pozzo del Fiume Siofra", "distance_km": 290.0, "lore_text": "Backtracking nelle viscere della terra sotto la volta stellata artificiale dei templi ancestrali.", "badge_icon": "ghost"},
            {"order_index": 5, "name": "Terre Rosse di Caelid & Castello Mantorosso", "distance_km": 390.0, "lore_text": "La marcia nella putrescenza scarlatta. Il festival della guerra ha inizio contro il Generale Radahn.", "badge_icon": "meteor"},
            {"order_index": 6, "name": "Cratere della Stella Caduta & Nokron", "distance_km": 470.0, "lore_text": "Backtracking verso Sepolcride: la stella caduta apre una voragine monumentale verso la Città Eterna.", "badge_icon": "map-pin"},
            {"order_index": 7, "name": "Salita al Grande Montacarichi & Altopiano di Altus", "distance_km": 570.0, "lore_text": "Il medaglione di Dectus si ricongiunge. Le pianure d'oro risplendono sotto le fronde dell'Albero Madre.", "badge_icon": "key"},
            {"order_index": 8, "name": "Assalto a Leyndell, Capitale Reale", "distance_km": 660.0, "lore_text": "I bastioni di pietra dorata cedono. Morgott il Re Presagio difende le radici impenetrabili dell'Albero.", "badge_icon": "crown"},
            {"order_index": 9, "name": "Vette dei Giganti & Forgia del Fuoco Sacro", "distance_km": 740.0, "lore_text": "Il gelo eterno delle montagne cede il passo al calore primordiale. La Fiamma brucia le spine ancestrali.", "badge_icon": "fire"},
            {"order_index": 10, "name": "Farum Azula & Ritorno alla Capitale delle Ceneri", "distance_km": 850.0, "lore_text": "Vortici di draghi tra il tempo spezzato. Backtracking finale sulle ceneri di Leyndell: reclamate il Trono Ancestrale!", "badge_icon": "award"},
        ]
    },
    {
        "slug": "hogwarts-express",
        "title": "L'Espresso per Hogwarts",
        "universe": "Mondo Magico",
        "description": "La leggendaria tratta ferroviaria scarlatta da King's Cross attraverso le brughiere e le Highlands scozzesi fino alle torri di Hogwarts.",
        "total_distance_km": 800.0,
        "badge_icon": "train",
        "milestones": [
            {"order_index": 0, "name": "Binario 9 ¾ - Stazione di King's Cross", "distance_km": 0.0, "lore_text": "Attraversa il muro di mattoni. Il fischio della locomotiva a vapore sbuffa fumo bianco nel cuore di Londra.", "badge_icon": "compass"},
            {"order_index": 1, "name": "Campagne dello Yorkshire & Carrello dei Dolci", "distance_km": 280.0, "lore_text": "Le colline inglesi scorrono veloci. Rane di cioccolato e Gelatine Tutti i Gusti +1 allietano lo scompartimento.", "badge_icon": "sparkles"},
            {"order_index": 2, "name": "Il confine delle Highlands & Lago di Rannoch", "distance_km": 540.0, "lore_text": "L'aria diventa frizzante e le brughiere scozzesi si estendono a perdita d'occhio sotto cieli tempestosi.", "badge_icon": "mountain-snow"},
            {"order_index": 3, "name": "Il Viadotto di Glenfinnan", "distance_km": 720.0, "lore_text": "Le celebri ventuno arcate di pietra semicircolari si ergono maestose sopra la valle selvaggia.", "badge_icon": "castle"},
            {"order_index": 4, "name": "Stazione di Hogsmeade & Castello di Hogwarts", "distance_km": 800.0, "lore_text": "Le barche scivolano silenziose sul Lago Nero: le finestre illuminate della Scuola di Magia brillano nella notte!", "badge_icon": "award"},
        ]
    },
    {
        "slug": "the-witcher",
        "title": "The Witcher: Il Sentiero dello Strigo",
        "universe": "Il Continente",
        "description": "In sella a Rutilia attraverso le brughiere desolate del Velen, i canali di Novigrad e le cime tempestose di Skellige.",
        "total_distance_km": 1200.0,
        "badge_icon": "shield",
        "milestones": [
            {"order_index": 0, "name": "Bianco Frutteto & Locanda del Fiume", "distance_km": 0.0, "lore_text": "Geralt e Vesemir seguono le tracce di Yennefer tra campi dilaniati dalla guerra nilfgaardiana.", "badge_icon": "home"},
            {"order_index": 1, "name": "Il Nido del Corvo & Paludi del Velen", "distance_km": 240.0, "lore_text": "Le sinistre megere della Palude del Gobbo e il Barone Sanguinario nella terra di nessuno.", "badge_icon": "skull"},
            {"order_index": 2, "name": "Novigrad, Città Libera & Il Passiflora", "distance_km": 460.0, "lore_text": "I canali affollati, i templi del Fuoco Eterno e le gilde clandestine della metropoli del nord.", "badge_icon": "castle"},
            {"order_index": 3, "name": "Isole Skellige & Fortezza di Kaer Trolde", "distance_km": 720.0, "lore_text": "Drakkar battuti dalle onde impetuose, canti di clan vichinghi e scogliere sferzate dal vento del mare.", "badge_icon": "waves"},
            {"order_index": 4, "name": "Kaer Morhen, Roccaforte dei Lupi", "distance_km": 950.0, "lore_text": "L'antica scuola dello strigo tra le vette alpine del Regno di Kaedwen prima della grande battaglia.", "badge_icon": "swords"},
            {"order_index": 5, "name": "Ducato di Toussaint & Vigneti di Corvo Bianco", "distance_km": 1200.0, "lore_text": "La terra fiabesca del vino, dei cavalieri erranti e dell'ombra immortale di Dettlaff. Il meritato riposo di Geralt.", "badge_icon": "trophy"},
        ]
    },
    {
        "slug": "skyrim",
        "title": "Skyrim: Il Pellegrinaggio del Sangue di Drago",
        "universe": "Tamriel",
        "description": "Dalla scampata esecuzione di Helgen fino alle sale eterne di Sovngarde al grido di Fus Ro Dah.",
        "total_distance_km": 600.0,
        "badge_icon": "flame",
        "milestones": [
            {"order_index": 0, "name": "La Fuga di Helgen & Riverwood", "distance_km": 0.0, "lore_text": "L'ombra nera di Alduin squarcia il cielo. Fuggi dal ceppo e incamminati lungo il fiume fino a Riverwood.", "badge_icon": "sparkles"},
            {"order_index": 1, "name": "Whiterun & Tumulo delle Cascate Tristi", "distance_km": 70.0, "lore_text": "La rocca di Dragonsreach e il primo urlo draconico risvegliato contro il drago della torre occidentale.", "badge_icon": "castle"},
            {"order_index": 2, "name": "I 7.000 Scalini & Santuario di Hrothgar Alto", "distance_km": 170.0, "lore_text": "Salita estenuante nella bufera fino al monastero dei Barbagrigia e al cospetto di Paarthurnax.", "badge_icon": "mountain-snow"},
            {"order_index": 3, "name": "La Fenditura & I Canali di Riften", "distance_km": 280.0, "lore_text": "La capitale della gilda dei ladri tra boschi autunnali di betulle dorate e intrighi del Ratway.", "badge_icon": "beer"},
            {"order_index": 4, "name": "L'Accademia Magica di Winterhold", "distance_km": 400.0, "lore_text": "La fortezza dei maghi arroccata su una guglia di pietra ghiacciata sopra il Mare dei Fantasmi.", "badge_icon": "moon"},
            {"order_index": 5, "name": "Le Rovine Dwemer di Blackreach", "distance_km": 500.0, "lore_text": "La città perduta sotterranea illuminata da funghi bioluminescenti giganti e guardiani meccanici.", "badge_icon": "ghost"},
            {"order_index": 6, "name": "Portale di Sovngarde & Caduta di Alduin", "distance_km": 600.0, "lore_text": "Attraversa il ponte di ossa di balena ed entra nel Salone dell'Onore: Alduin il Divoratore di Mondi è sconfitto!", "badge_icon": "trophy"},
        ]
    },
    {
        "slug": "pokemon-kanto",
        "title": "Pokémon: Il Cammino della Lega di Kanto",
        "universe": "Mondo Pokémon",
        "description": "Da Biancavilla fino all'Altopiano Blu conquistando tutte le 8 medaglie e sconfiggendo i Superquattro.",
        "total_distance_km": 420.0,
        "badge_icon": "award",
        "milestones": [
            {"order_index": 0, "name": "Biancavilla & Laboratorio del Prof. Oak", "distance_km": 0.0, "lore_text": "Ricevi il tuo primo compagno di avventure e muovi i primi passi nell'erba alta del Percorso 1.", "badge_icon": "home"},
            {"order_index": 1, "name": "Bosco Smeraldo & Palestra Roccia di Plumbeopoli", "distance_km": 45.0, "lore_text": "Tra Caterpie e Pikachu selvatici fino alla prima vittoria contro Brock e il suo Onix.", "badge_icon": "shield"},
            {"order_index": 2, "name": "Monte Luna & Palestra Cascata di Celestopoli", "distance_km": 105.0, "lore_text": "La Pietralunare risplende nella grotta dei Clefairy; Misty e Starmie attendono nella piscina olimpica.", "badge_icon": "waves"},
            {"order_index": 3, "name": "M/N Anna & Palestra Tuono di Aranciopoli", "distance_km": 165.0, "lore_text": "Il porto affacciato sul mare, la lezione di Taglio dal capitano e la sfida elettrizzante contro il Tenente Surge.", "badge_icon": "zap"},
            {"order_index": 4, "name": "Pista Ciclabile & Palestra Iride di Azzurropoli", "distance_km": 230.0, "lore_text": "Pedala a tutta velocità sul cavalcavia prima di sfidare Erika e il nascondiglio segreto del Team Rocket.", "badge_icon": "bike"},
            {"order_index": 5, "name": "Torre Pokémon & Palestra Palude di Zafferanopoli", "distance_km": 300.0, "lore_text": "I fantasmi di Lavandonia e la liberazione della Silph SpA dai poteri psichici di Sabrina.", "badge_icon": "ghost"},
            {"order_index": 6, "name": "Isola Cannella & Laboratorio del Vulcano", "distance_km": 360.0, "lore_text": "Naviga verso l'isola vulcanica per rispondere ai quiz del Dr. Blaine tra le fiamme di Magmar.", "badge_icon": "flame"},
            {"order_index": 7, "name": "Via Vittoria & Campione dell'Altopiano Blu", "distance_km": 420.0, "lore_text": "Supera la grotta di Moltres e batti Lorelei, Bruno, Agatha, Lance e il tuo rivale: sei il Campione di Kanto!", "badge_icon": "trophy"},
        ]
    },
    {
        "slug": "dragon-ball",
        "title": "Dragon Ball: La Via del Serpentone",
        "universe": "Universo 7",
        "description": "L'infinita via dorata dell'Aldilà lunga 1.000 km sospesa sopra l'Inferno per allenarsi dal Re Kaioh.",
        "total_distance_km": 1000.0,
        "badge_icon": "zap",
        "milestones": [
            {"order_index": 0, "name": "Palazzo di Re Enma & Partenza dalla Coda", "distance_km": 0.0, "lore_text": "Goku saluta la scrivania monumentale di Re Enma e inizia a correre sull'infinita coda dorata del drago.", "badge_icon": "compass"},
            {"order_index": 1, "name": "Il Primo Balzo sopra il Mare di Nubi", "distance_km": 180.0, "lore_text": "La strada si restringe pericolosamente: sotto le nuvole gialle si aprono le fiamme dell'Inferno.", "badge_icon": "mountain-snow"},
            {"order_index": 2, "name": "Il Castello della Principessa Serpente", "distance_km": 420.0, "lore_text": "La tentazione delle danzatrici e del banchetto illusorio. Fuggi prima di finire divorato!", "badge_icon": "castle"},
            {"order_index": 3, "name": "Lo Spazzino dell'Aldilà & Ritorno in Pista", "distance_km": 680.0, "lore_text": "Evita di scivolare dal bordo per non dover risalire dall'Inferno. Il fiato si fa corto ma la Terra ha bisogno di te.", "badge_icon": "flame"},
            {"order_index": 4, "name": "La Testa del Drago & Il Salto nel Vuoto", "distance_km": 940.0, "lore_text": "La fine della strada! Un minuscolo pianetino gravita solitario poco più in alto nel cielo cosmico.", "badge_icon": "meteor"},
            {"order_index": 5, "name": "Il Pianeta di Re Kaioh (Gravità x10)", "distance_km": 1000.0, "lore_text": "Schiacciato dalla gravità decuplicata, cattura la scimmia Bubbles e impara il Kaiohken e la Genkidama!", "badge_icon": "trophy"},
        ]
    },
    {
        "slug": "dune",
        "title": "Dune: Il Cammino di Muad'Dib su Arrakis",
        "universe": "Arrakis",
        "description": "Dalle sale di Arrakeen attraverso le tempeste di Coriolis nel deserto profondo in sella ai vermi Shai-Hulud.",
        "total_distance_km": 750.0,
        "badge_icon": "flame",
        "milestones": [
            {"order_index": 0, "name": "Il Palazzo Ducale di Arrakeen", "distance_km": 0.0, "lore_text": "L'arrivo della casata Atreides sul pianeta delle spezie e l'imboscata mortale degli Harkonnen.", "badge_icon": "castle"},
            {"order_index": 1, "name": "La Fuga nell'Ornitottero & Tempesta di Coriolis", "distance_km": 110.0, "lore_text": "Venti a 800 km/h squarciano la roccia. Paul e Jessica precipitano tra le dune infinite.", "badge_icon": "waves"},
            {"order_index": 2, "name": "Il Santuario di Sietch Tabr", "distance_km": 260.0, "lore_text": "L'accoglienza tra i Fremen di Stilgar, il duello con Jamis e gli occhi che diventano blu-ibisco.", "badge_icon": "home"},
            {"order_index": 3, "name": "La Prima Cavalcata di Shai-Hulud", "distance_km": 450.0, "lore_text": "Pianta i ganci da creatore sul dorso del verme delle sabbie colossale e cavalcalo nel Mare di Dune.", "badge_icon": "swords"},
            {"order_index": 4, "name": "I Pozzi della Spezia nel Deserto del Sud", "distance_km": 600.0, "lore_text": "L'Acqua della Vita svela il passato e il futuro. I Fremen inneggiano al Kwisatz Haderach.", "badge_icon": "sparkles"},
            {"order_index": 5, "name": "L'Assalto di Carthage & Trono dell'Imperatore", "distance_km": 750.0, "lore_text": "Le armate Sardaukar cedono il passo. Muad'Dib impone la pace galattica: chi controlla la spezia controlla l'universo!", "badge_icon": "trophy"},
        ]
    },
    {
        "slug": "zelda-botw",
        "title": "Zelda: La Rinascita di Hyrule",
        "universe": "Regno di Hyrule",
        "description": "Risveglia i quattro Colossi Sacri negli angoli più remoti del regno per liberare il Castello dalla Calamità Ganon.",
        "total_distance_km": 550.0,
        "badge_icon": "shield",
        "milestones": [
            {"order_index": 0, "name": "Sacrario della Rinascita & Grande Altopiano", "distance_km": 0.0, "lore_text": "Link si risveglia da un sonno centenario con la Tavoletta Sheikah in pugno. Apri le ali del paravela.", "badge_icon": "sparkles"},
            {"order_index": 1, "name": "Villaggio Calipso & Monti Gemelli", "distance_km": 65.0, "lore_text": "Incontra Impa tra i ciliegi in fiore per comprendere la caduta dei Campioni di cento anni prima.", "badge_icon": "home"},
            {"order_index": 2, "name": "Dominio degli Zora & Colosso Vah Ruta", "distance_km": 160.0, "lore_text": "Nuota risalendo le cascate insieme a Sidon per placare la pioggia infinita con frecce elettriche.", "badge_icon": "waves"},
            {"order_index": 3, "name": "Pendici del Monte Morte & Vah Rudania", "distance_km": 270.0, "lore_text": "Il calore del magma dei Goron; Yunobo cannoneggia il colosso lucertola tra le rocce infuocate.", "badge_icon": "flame"},
            {"order_index": 4, "name": "Borgo dei Rito & Colosso Vah Medoh", "distance_km": 370.0, "lore_text": "Gareggia nei cieli ghiacciati sopra il lago prima di neutralizzare i cannoni laser del colosso alato.", "badge_icon": "mountain-snow"},
            {"order_index": 5, "name": "Cittadella Gerudo & Colosso Vah Naboris", "distance_km": 460.0, "lore_text": "Attraversa il deserto guidato dalle foche delle sabbie prima di sconfiggere l'Ira del Tuono di Ganon.", "badge_icon": "zap"},
            {"order_index": 6, "name": "Castello di Hyrule & La Spada che Esorcizza il Buio", "distance_km": 550.0, "lore_text": "Estrai la Master Sword dal Bosco Perduto ed entra nella sala del trono: Hyrule è finalmente salva!", "badge_icon": "trophy"},
        ]
    },
    {
        "slug": "star-wars",
        "title": "Star Wars: La Rotta di Kessel & Il Cammino Jedi",
        "universe": "Galassia Lontana",
        "description": "Sfreccia a velocità iperluce attraverso il Vortice di Maw e ripristina l'equilibrio nella Forza fino a Coruscant.",
        "total_distance_km": 300.0,
        "badge_icon": "zap",
        "milestones": [
            {"order_index": 0, "name": "Spazioporto di Mos Eisley su Tatooine", "distance_km": 0.0, "lore_text": "Un covo di feccia e malvagità. Accendi i propulsori del Millennium Falcon nel pozzo di lancio 94.", "badge_icon": "home"},
            {"order_index": 1, "name": "Le Miniere di Coassio su Kessel", "distance_km": 75.0, "lore_text": "Carica a bordo il carburante grezzo instabile prima che le corazzate imperiali blocchino l'orbita.", "badge_icon": "skull"},
            {"order_index": 2, "name": "Il Vortice di Maw & Summa-Verminoth", "distance_km": 160.0, "lore_text": "Schiva le fauci del leviatano dello spazio profondo sfiorando l'orizzonte degli eventi del buco nero.", "badge_icon": "meteor"},
            {"order_index": 3, "name": "Salto nell'Iperspazio in meno di 12 Parsec", "distance_km": 230.0, "lore_text": "Inietta il coassio nei reattori ausiliari: le stelle si allungano in scie celesti a velocità impensabile.", "badge_icon": "sparkles"},
            {"order_index": 4, "name": "Il Tempio Jedi di Coruscant", "distance_km": 300.0, "lore_text": "Le guglie dorate della capitale galattica risplendono. Che la Forza sia con te, sempre!", "badge_icon": "trophy"},
        ]
    }
]

def seed_default_journeys(db: Session):
    for journey_data in DEFAULT_JOURNEYS:
        existing = db.query(Journey).filter(Journey.slug == journey_data["slug"]).first()
        if not existing:
            journey = Journey(
                slug=journey_data["slug"],
                title=journey_data["title"],
                universe=journey_data["universe"],
                description=journey_data["description"],
                total_distance_km=journey_data["total_distance_km"],
                badge_icon=journey_data["badge_icon"]
            )
            db.add(journey)
            db.commit()
            db.refresh(journey)

            for ms in journey_data["milestones"]:
                milestone = JourneyMilestone(
                    journey_id=journey.id,
                    order_index=ms["order_index"],
                    name=ms["name"],
                    distance_km=ms["distance_km"],
                    lore_text=ms["lore_text"],
                    badge_icon=ms["badge_icon"]
                )
                db.add(milestone)
            db.commit()
        else:
            # Aggiorna dati se sono cambiati (es. Elden Ring con backtracking)
            existing.title = journey_data["title"]
            existing.universe = journey_data["universe"]
            existing.description = journey_data["description"]
            existing.total_distance_km = journey_data["total_distance_km"]
            existing.badge_icon = journey_data["badge_icon"]
            
            # Sincronizza milestones
            db.query(JourneyMilestone).filter(JourneyMilestone.journey_id == existing.id).delete()
            for ms in journey_data["milestones"]:
                milestone = JourneyMilestone(
                    journey_id=existing.id,
                    order_index=ms["order_index"],
                    name=ms["name"],
                    distance_km=ms["distance_km"],
                    lore_text=ms["lore_text"],
                    badge_icon=ms["badge_icon"]
                )
                db.add(milestone)
            db.commit()

def get_or_create_user_progress(db: Session, user_id: int, journey_id: int) -> UserJourneyProgress:
    progress = db.query(UserJourneyProgress).filter(
        UserJourneyProgress.user_id == user_id,
        UserJourneyProgress.journey_id == journey_id
    ).first()

    if not progress:
        first_ms = db.query(JourneyMilestone).filter(
            JourneyMilestone.journey_id == journey_id,
            JourneyMilestone.order_index == 0
        ).first()

        db.query(UserJourneyProgress).filter(
            UserJourneyProgress.user_id == user_id
        ).update({"is_active": False})

        progress = UserJourneyProgress(
            user_id=user_id,
            journey_id=journey_id,
            cumulative_distance_km=0.0,
            current_milestone_id=first_ms.id if first_ms else None,
            is_active=True,
            is_completed=False,
            started_at=datetime.utcnow()
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress

def format_progress_response(progress: UserJourneyProgress, db: Session) -> UserJourneyProgressResponse:
    journey = progress.journey
    milestones = db.query(JourneyMilestone).filter(
        JourneyMilestone.journey_id == journey.id
    ).order_by(JourneyMilestone.order_index).all()

    user_profile = progress.user.profile if progress.user else None

    cum_dist = round(progress.cumulative_distance_km, 2)
    tot_dist = journey.total_distance_km
    remaining = max(0.0, round(tot_dist - cum_dist, 2))
    percentage = min(100.0, round((cum_dist / tot_dist) * 100.0, 1)) if tot_dist > 0 else 100.0

    cal_total = calculate_journey_calories(tot_dist, user_profile)
    cal_remaining = calculate_journey_calories(remaining, user_profile)

    ms_responses = []
    current_ms = None
    next_ms = None
    unlocked_count = 0

    for m in milestones:
        is_unlocked = cum_dist >= m.distance_km
        if is_unlocked:
            unlocked_count += 1
            current_ms = m
        elif next_ms is None:
            next_ms = m

        ms_responses.append(JourneyMilestoneResponse(
            id=m.id,
            order_index=m.order_index,
            name=m.name,
            distance_km=m.distance_km,
            estimated_calories=calculate_journey_calories(m.distance_km, user_profile),
            description=m.description,
            lore_text=m.lore_text,
            image_url=m.image_url,
            badge_icon=m.badge_icon,
            is_unlocked=is_unlocked
        ))

    dist_to_next = round(next_ms.distance_km - cum_dist, 2) if next_ms else 0.0

    curr_resp = JourneyMilestoneResponse(
        id=current_ms.id,
        order_index=current_ms.order_index,
        name=current_ms.name,
        distance_km=current_ms.distance_km,
        estimated_calories=calculate_journey_calories(current_ms.distance_km, user_profile),
        description=current_ms.description,
        lore_text=current_ms.lore_text,
        image_url=current_ms.image_url,
        badge_icon=current_ms.badge_icon,
        is_unlocked=True
    ) if current_ms else None

    next_resp = JourneyMilestoneResponse(
        id=next_ms.id,
        order_index=next_ms.order_index,
        name=next_ms.name,
        distance_km=next_ms.distance_km,
        estimated_calories=calculate_journey_calories(next_ms.distance_km, user_profile),
        description=next_ms.description,
        lore_text=next_ms.lore_text,
        image_url=next_ms.image_url,
        badge_icon=next_ms.badge_icon,
        is_unlocked=False
    ) if next_ms else None

    journey_resp = JourneyResponse(
        id=journey.id,
        slug=journey.slug,
        title=journey.title,
        description=journey.description,
        universe=journey.universe,
        total_distance_km=journey.total_distance_km,
        estimated_calories_total=cal_total,
        cover_image=journey.cover_image,
        badge_icon=journey.badge_icon,
        milestones=ms_responses
    )

    return UserJourneyProgressResponse(
        id=progress.id,
        journey=journey_resp,
        cumulative_distance_km=cum_dist,
        remaining_distance_km=remaining,
        progress_percentage=percentage,
        estimated_calories_total=cal_total,
        estimated_calories_remaining=cal_remaining,
        is_active=progress.is_active,
        is_completed=progress.is_completed,
        current_milestone=curr_resp,
        next_milestone=next_resp,
        distance_to_next_km=dist_to_next,
        unlocked_milestones_count=unlocked_count,
        total_milestones_count=len(milestones)
    )

def record_ride_progress(
    db: Session,
    user_id: int,
    distance_km: float,
    journey_id: Optional[int] = None
) -> Tuple[Optional[UserJourneyProgressResponse], Optional[MilestoneUnlockCelebration]]:
    progress = None
    if journey_id:
        progress = db.query(UserJourneyProgress).filter(
            UserJourneyProgress.user_id == user_id,
            UserJourneyProgress.journey_id == journey_id
        ).first()
    
    if not progress:
        progress = db.query(UserJourneyProgress).filter(
            UserJourneyProgress.user_id == user_id,
            UserJourneyProgress.is_active == True
        ).first()

    if not progress:
        default_j = db.query(Journey).filter(Journey.slug == "lord-of-the-rings").first()
        if default_j:
            progress = get_or_create_user_progress(db, user_id, default_j.id)

    if not progress:
        return None, None

    old_dist = progress.cumulative_distance_km
    new_dist = round(old_dist + distance_km, 2)
    progress.cumulative_distance_km = new_dist

    newly_unlocked = None
    milestones = db.query(JourneyMilestone).filter(
        JourneyMilestone.journey_id == progress.journey_id
    ).order_by(JourneyMilestone.distance_km).all()

    for m in milestones:
        if old_dist < m.distance_km <= new_dist:
            progress.current_milestone_id = m.id
            newly_unlocked = MilestoneUnlockCelebration(
                milestone_name=m.name,
                distance_km=m.distance_km,
                lore_text=m.lore_text,
                badge_icon=m.badge_icon,
                journey_title=progress.journey.title
            )

    if new_dist >= progress.journey.total_distance_km and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(progress)

    progress_resp = format_progress_response(progress, db)
    return progress_resp, newly_unlocked
