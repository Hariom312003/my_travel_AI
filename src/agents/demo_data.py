"""Demo and fallback data for Voyage AI Travel Planner.

Contains static registry of attractions, categories, and food recommendations
for fallback/offline demonstration purposes. Covers major global destinations.
"""

DEMO_ATTRACTIONS = {
    "Goa": [
        "Curly's Beach Shack",
        "Chapora Fort",
        "Anjuna Flea Market",
        "Fontainhas",
        "Basilica of Bom Jesus",
        "Baga Beach",
        "Calangute Beach",
        "Dona Paula",
        "Palolem Beach"
    ],
    "Manali": [
        "Solang Valley",
        "Hadimba Temple",
        "Jogini Waterfall",
        "Old Manali Cafes",
        "Rohtang Pass",
        "Vashisht Hot Springs",
        "Tibetan Monastery",
        "Van Vihar"
    ],
    "Jaipur": [
        "Hawa Mahal",
        "Amer Fort",
        "City Palace",
        "Jantar Mantar",
        "Chokhi Dhani",
        "Nahargarh Fort"
    ],
    "Iceland": [
        "Gullfoss Waterfall",
        "Seljalandsfoss Waterfall",
        "Skogafoss Waterfall",
        "Black Sand Beach (Reynisfjara)",
        "Jokulsarlon Glacier Lagoon",
        "Blue Lagoon"
    ],
    "Vietnam": [
        "Ha Long Bay",
        "Hoi An Ancient Town",
        "Ho Chi Minh Mausoleum",
        "Cu Chi Tunnels",
        "Phong Nha Caves",
        "War Remnants Museum"
    ],
    "Peru": [
        "Machu Picchu",
        "Sacred Valley",
        "Rainbow Mountain",
        "Colca Canyon",
        "Huacachina Oasis",
        "Nazca Lines"
    ],
    "Bangalore": [
        "Bangalore Palace",
        "Cubbon Park",
        "Lalbagh Botanical Garden",
        "Tipu Sultan's Summer Palace",
        "Nandi Hills",
        "Phoenix Marketcity"
    ],
    "Kerala": [
        "Alleppey Backwaters Houseboat",
        "Munnar Tea Gardens",
        "Wayanad Wildlife Sanctuary",
        "Kovalam Beach",
        "Athirappilly Waterfalls",
        "Varkala Cliff"
    ],
    "Bangkok": [
        "Grand Palace", "Wat Phra Kaew", "Wat Arun", "Wat Pho", "Chatuchak Weekend Market",
        "Chao Phraya River Cruise", "Khao San Road", "Jim Thompson House", "Lumpini Park",
        "Wat Saket (Golden Mount)", "Erawan Shrine", "ICONSIAM Shopping Mall", "Siam Paragon",
        "MBK Center", "Chinatown (Yaowarat Road)", "Asiatique The Riverfront", "Mahanakhon SkyWalk",
        "Jim Thompson Art Center", "Art in Paradise Bangkok", "Sea Life Bangkok Ocean World",
        "Wat Benchamabophit (Marble Temple)", "Wat Traimit (Golden Buddha)", "National Museum Bangkok",
        "Vimanmek Mansion", "Dusit Zoo Park", "Suan Pakkad Palace", "Patong Night Market",
        "Pratunam Market", "Talad Rot Fai (Train Night Market Srinakarin)", "Siam Discovery",
        "CentralwOrld Mall", "Wang Lang Market", "Pak Khlong Talat (Flower Market)",
        "Wat Suthat & Giant Swing", "Bangkok Art and Culture Centre", "Queen Sirikit Park",
        "Benjakitti Park Forest", "Khlong Lat Mayom Floating Market", "Taling Chan Floating Market",
        "Wat Prayurawongsawas", "Phra Sumen Fort", "Santi Chai Prakan Park", "Madame Tussauds Bangkok",
        "King Rama IX Park", "Safari World Bangkok", "Dream World Amusement Park",
        "Wat Mangkon Kamalawat", "Loha Prasat Temple", "Museum Siam Discovery",
        "Terminal 21 Asok Mall", "EmQuartier Shopping District", "Phaya Thai Palace",
        "Bang Krachao Green Lung", "Don Wai Floating Market", "Wat Kalayanamitr",
        "Talad Noi Alleys", "Neilson Hays Library", "Princess Mother Memorial Park",
        "Wat Rakhang Kositaram", "Wongwian Yai Landmark", "Loha Prasat Metal Castle"
    ],
    "Tokyo": [
        "Senso-ji Temple", "Shibuya Crossing", "Meiji Jingu Shrine", "Shinjuku Gyoen National Garden",
        "Tokyo Skytree", "Tsukiji Outer Market", "Akihabara Electric Town", "Harajuku Takeshita Street",
        "Tokyo Tower", "Imperial Palace East Gardens", "Ueno Park & Zoo", "Tokyo National Museum",
        "Odaiba Seaside Park", "Ghibli Museum", "teamLab Planets TOKYO", "Roppongi Hills Mori Tower",
        "Yoyogi Park", "Nakamise Shopping Street", "Rainbow Bridge Odaiba", "Tokyo Disney Resort",
        "Tokyo Sea Life Park", "Hamarikyu Gardens", "Zojo-ji Temple", "Shinjuku Golden Gai",
        "Omoide Yokocho Street", "Kabukicho District", "Tokyo Metropolitan Government Building",
        "Nezu Shrine", "Rikugien Garden", "Koishikawa Korakuen Garden", "Sumida Park",
        "Ameyoko Shopping Street", "National Museum of Nature and Science", "National Museum of Western Art",
        "Edo-Tokyo Museum", "Meguro River Cherry Blossoms", "Hachiko Statue Shibuya", "Omotesando Hills",
        "Tokyo Midtown", "Ginza Six Shopping Mall", "Sengaku-ji Temple", "Kiyosumi Gardens",
        "Tokyo Dome City", "Kasai Rinkai Park", "Gotokuji Temple (Cat Temple)"
    ],
    "Kyoto": [
        "Fushimi Inari Taisha Shrine",
        "Kinkaku-ji (Golden Pavilion)",
        "Kiyomizu-dera Temple",
        "Arashiyama Bamboo Grove",
        "Gion District Walking Tour",
        "Nijo Castle",
        "Kyoto Imperial Palace",
        "Nishiki Market"
    ],
    "Seoul": [
        "Gyeongbokgung Palace",
        "N Seoul Tower",
        "Bukchon Hanok Village",
        "Myeongdong Shopping Street",
        "Insa-dong Culture Street",
        "Dongdaemun Design Plaza",
        "Changdeokgung Palace",
        "Han River Park"
    ],
    "Singapore": [
        "Gardens by the Bay",
        "Marina Bay Sands",
        "Sentosa Island Beaches",
        "Singapore Botanic Gardens",
        "Chinatown Heritage Centre",
        "Little India Heritage Walk",
        "Orchard Road Shopping",
        "Kampong Glam & Haji Lane"
    ],
    "Bali": [
        "Ubud Monkey Forest",
        "Tanah Lot Temple",
        "Uluwatu Temple Sunset",
        "Tegallalang Rice Terraces",
        "Mount Batur Sunrise Trek",
        "Seminyak Beach",
        "Nusa Penida Kelingking",
        "Besakih Great Temple"
    ],
    "Paris": [
        "Eiffel Tower", "Louvre Museum", "Cathédrale Notre-Dame", "Arc de Triomphe",
        "Sacré-Cœur & Montmartre", "Seine River Cruise", "Jardin des Tuileries", "Musée d'Orsay",
        "Palace of Versailles", "Jardin du Luxembourg", "Champs-Élysées Boulevard", "Centre Pompidou",
        "Sainte-Chapelle", "Panthéon", "Catacombs of Paris", "Musée de l'Orangerie", "Musée Rodin",
        "Musée Picasso", "Jardin des Plantes", "Place de la Concorde", "Place des Vosges",
        "Palais Garnier (Opera House)", "Les Invalides (Napoleon Tomb)", "Pont Neuf Bridge",
        "Pont Alexandre III", "Galeries Lafayette Haussmann", "Père Lachaise Cemetery",
        "Canal Saint-Martin", "Bois de Boulogne", "Bois de Vincennes", "Jardin d'Acclimatation",
        "Musée du Quai Branly", "Grand Palais Paris", "Petit Palais", "La Défense district",
        "Grande Arche de la Défense", "Shakespeare and Company bookstore", "Jules Verne Restaurant (Eiffel)",
        "Fondation Louis Vuitton", "Palais de Tokyo", "Musée de Cluny", "Jardin du Palais-Royal",
        "Parc des Buttes-Chaumont", "Parc Monceau", "Place de la Bastille",
        "Saint-Germain-des-Prés Church", "Montparnasse Tower Observation Deck", "La Conciergerie Prison",
        "Musée de l'Armée Invalides", "Musée Jacquemart-André", "Parc de la Villette",
        "Cité des Sciences et de l'Industrie", "Musée Marmottan Monet", "Palais de la Découverte",
        "Jardin des Serres d'Auteuil", "Musée de l'Homme", "Place du Tertre Montmartre",
        "Rue Cler Market Street", "Bercy Village Square", "Musée National du Moyen Âge"
    ],
    "Rome": [
        "Colosseum & Roman Forum",
        "Vatican Museums & Sistine Chapel",
        "Pantheon",
        "Trevi Fountain",
        "Piazza Navona",
        "Spanish Steps",
        "Villa Borghese Gardens",
        "Castel Sant'Angelo"
    ],
    "London": [
        "British Museum",
        "Tower of London",
        "London Eye",
        "Buckingham Palace",
        "Westminster Abbey",
        "Hyde Park Walk",
        "Tate Modern",
        "Covent Garden Market"
    ],
    "Dubai": [
        "Burj Khalifa",
        "The Dubai Mall & Fountain Show",
        "Palm Jumeirah",
        "Desert Safari",
        "Burj Al Arab Beach",
        "Al Fahidi Historical District",
        "Gold & Spice Souks",
        "Dubai Marina Walk"
    ],
    "New York": [
        "Statue of Liberty & Ellis Island",
        "Central Park",
        "Empire State Building",
        "Times Square",
        "High Line Park",
        "Brooklyn Bridge",
        "Metropolitan Museum of Art",
        "Chelsea Market"
    ],
    "Sydney": [
        "Sydney Opera House",
        "Sydney Harbour Bridge",
        "Bondi Beach Coastal Walk",
        "Royal Botanic Garden",
        "Darling Harbour",
        "Taronga Zoo",
        "The Rocks District",
        "Manly Beach & Ferry"
    ],
    "Cape Town": [
        "Table Mountain Aerial Cableway",
        "V&A Waterfront",
        "Cape Point Nature Reserve",
        "Boulders Beach Penguin Colony",
        "Kirstenbosch Botanical Garden",
        "Robben Island Museum",
        "Bo-Kaap Quarter",
        "Chapman's Peak Drive"
    ],
    "Rio": [
        "Christ the Redeemer",
        "Sugarloaf Mountain",
        "Copacabana Beach",
        "Ipanema Beach Walk",
        "Tijuca National Park",
        "Selarón Steps",
        "Maracanã Stadium",
        "Santa Teresa Quarter"
    ],
    "Mumbai": [
        "Gateway of India",
        "Marine Drive Promenade",
        "Chhatrapati Shivaji Terminus",
        "Elephanta Caves",
        "Colaba Causeway Shopping",
        "Sanjay Gandhi National Park",
        "Juhu Beach",
        "Haji Ali Dargah"
    ],
    "Delhi": [
        "Red Fort",
        "Qutub Minar",
        "India Gate",
        "Humayun's Tomb",
        "Lotus Temple",
        "Chandni Chowk Market",
        "Swaminarayan Akshardham",
        "Rashtrapati Bhavan"
    ],
    "Chennai": [
        "Marina Beach",
        "Kapaleeshwarar Temple",
        "Government Museum",
        "San Thome Basilica",
        "Semmozhi Poonga Park",
        "Besant Nagar Beach",
        "Valluvar Kottam",
        "DakshinaChitra Museum"
    ],
    "Osaka": [
        "Osaka Castle & Park",
        "Dotonbori Neon Street",
        "Universal Studios Japan",
        "Umeda Sky Building Observatory",
        "Shitennoji Temple",
        "Kuromon Ichiba Market",
        "Osaka Aquarium Kaiyukan",
        "Shinsekai District"
    ],
    "Phuket": [
        "Patong Beach Coastline",
        "Big Buddha Phuket",
        "Wat Chalong Temple",
        "Phuket Old Town Walking Tour",
        "Kata Noi Beach Resort",
        "Promthep Cape Sunset Lookout",
        "Karon Viewpoint",
        "Bangla Road Nightlife"
    ],
    "Melbourne": [
        "Federation Square",
        "Royal Botanic Gardens Melbourne",
        "National Gallery of Victoria",
        "Melbourne Cricket Ground",
        "Eureka Skydeck 88",
        "Queen Victoria Market",
        "Fitzroy Gardens Walk",
        "St Kilda Beach Pier"
    ],
    "Reykjavik": [
        "Hallgrimskirkja Church Tower",
        "Harpa Concert Hall",
        "Sun Voyager Sculpture",
        "Perlan Museum & Dome",
        "National Museum of Iceland",
        "Laugavegur Shopping Street",
        "Tjornin Lake Walk",
        "Nautholsvik Thermal Beach"
    ],
    "Lima": [
        "Plaza Mayor of Lima",
        "Larco Museum Exhibition",
        "Huaca Pucllana Archaeological Site",
        "Miraflores Boardwalk & Love Park",
        "San San Francisco Convent Catacombs",
        "Barranco Bohemian District",
        "Magic Water Circuit Park",
        "Larcomar Shopping Center"
    ],
    "Kullu": [
        "Great Himalayan National Park",
        "Raghunath Temple",
        "Bhekhli Temple Viewpoint",
        "Pandoh Dam",
        "Naggar Castle History",
        "Manikaran Sahib Hot Springs",
        "Kasol Parvati River Walk"
    ],
    "Udaipur": [
        "City Palace complex",
        "Lake Pichola boat cruise",
        "Jagmandir Palace Island",
        "Sajjangarh Monsoon Palace",
        "Saheliyon-ki-Bari Gardens",
        "Jagdish Temple",
        "Bagore Ki Haveli museum",
        "Fateh Sagar Lake promenade"
    ],
    "Varanasi": [
        "Kashi Vishwanath Temple",
        "Dashashwamedh Ghat & Ganga Aarti",
        "Assi Ghat & Sunrise",
        "Sarnath Buddhist Site",
        "Manikarnika Ghat Heritage",
        "Banaras Hindu University & Birla Temple",
        "Ramnagar Fort",
        "Sankat Mochan Hanuman Temple",
        "Tulsi Manas Mandir"
    ],
    "Ayodhya": [
        "Ram Janmabhoomi Mandir",
        "Hanuman Garhi Temple",
        "Kanak Bhawan",
        "Saryu River Ghats & Aarti",
        "Nageshwarnath Temple",
        "Treta Ke Thakur",
        "Guptar Ghat Walk",
        "Mani Parvat",
        "Gulab Bari heritage garden"
    ],
    "Gorakhpur": [
        "Gorakhnath Temple",
        "Gita Press",
        "Ramgarh Taal Lake & Marine Drive",
        "Gorakhpur Railway Museum",
        "Kushmi Forest nature walk",
        "Arogya Mandir",
        "Vindhyavasini Park",
        "Imambara heritage site",
        "Neer Nikunj Park"
    ],
    "Mirzapur": [
        "Vindhyachal Dham & Vindhyavasini Temple",
        "Ashtabhuja Temple",
        "Kali Khoh Temple",
        "Chunar Fort",
        "Wyndham Falls",
        "Lakhaniya Dari Waterfalls",
        "Sirsi Dam & Scenic Falls",
        "Ghanta Ghar Mirzapur",
        "Mirzapur Ganga River Ghats"
    ],
    "Rishikesh": [
        "Laxman Jhula & Ram Jhula",
        "Triveni Ghat Ganga Aarti",
        "Parmarth Niketan Ashram",
        "Neer Garh Waterfall hike",
        "Beatles Ashram ruin walk",
        "Shivpuri rafting startpoint",
        "Kunjapuri Temple sunrise"
    ],
    "Shimla": [
        "The Ridge promenade",
        "Mall Road shopping walk",
        "Jakhoo Temple monkey hill",
        "Kalka Shimla Toy Train route",
        "Christ Church architecture",
        "Kufri scenic viewpoints",
        "Green Valley forest view",
        "Viceregal Lodge heritage tour"
    ]
}

DEMO_FOOD = {
    "Goa": {
        "Breakfast": "Goan poi bread with local jam or fresh fruit smoothies",
        "Lunch": "Spicy Goan Fish Curry Rice or rava fried calamari",
        "Dinner": "Freshly prepared Prawn Balchao followed by traditional sweet Bebinca"
    },
    "Manali": {
        "Breakfast": "Hot steamed sweet Siddu or Babru with tea",
        "Lunch": "Traditional Himachali Tudkiya Bhath at a local dhaba",
        "Dinner": "Wood-fired local Trout Fish with herbs or traditional Siddu with hot ghee"
    },
    "Jaipur": {
        "Breakfast": "Hot Pyaaz kachori and sweet saffron Lassi",
        "Lunch": "Traditional Rajasthani Dal Baati Churma cooked in pure ghee",
        "Dinner": "Authentic royal thali followed by sweet Ghewar"
    },
    "Iceland": {
        "Breakfast": "Skyr yogurt with local fresh berries and warm coffee",
        "Lunch": "Icelandic Lamb Soup or fresh catch of the day Arctic Char",
        "Dinner": "Fresh seafood cod or traditional rye bread with smoked salmon"
    },
    "Vietnam": {
        "Breakfast": "Traditional beef Pho with fresh herbs and Vietnamese coffee",
        "Lunch": "Banh Mi sandwich with pork pâté and fresh pickled vegetables",
        "Dinner": "Bun Cha grilled pork noodles or fresh seafood spring rolls"
    },
    "Peru": {
        "Breakfast": "Tamal Peruano with sweet corn and hot chocolate",
        "Lunch": "Fresh fish Ceviche marinated in lime juice with sweet potatoes",
        "Dinner": "Lomo Saltado stir-fried beef or quinoa soup with alpaca tenderloin"
    },
    "Bangalore": {
        "Breakfast": "Crispy Masala Dosa with coconut chutney and filter coffee",
        "Lunch": "Traditional Karnataka style Ragi Mudde with sambar or Bisi Bele Bath",
        "Dinner": "Craft beer at a local microbrewery with spicy chicken ghee roast"
    },
    "Kerala": {
        "Breakfast": "Appam with vegetable stew or steamed Puttu with kadala curry",
        "Lunch": "Kerala Sadya meal served on a banana leaf with parboiled rice",
        "Dinner": "Karimeen Pollichathu pearl spot fish fry or traditional Malabar chicken biryani"
    },
    "Bangkok": {
        "Breakfast": "Sweet Mango Sticky Rice with coconut cream and warm tea",
        "Lunch": "Traditional green curry with jasmine rice or classic Pad Thai at a local diner",
        "Dinner": "Spicy Tom Yum Goong soup with fresh river prawns and lemongrass"
    },
    "Tokyo": {
        "Breakfast": "Traditional Japanese breakfast with grilled salmon, miso soup, and rice",
        "Lunch": "Fresh sushi platter or hot pork tonkotsu ramen",
        "Dinner": "Charcoal-grilled Yakitori skewers or premium wagyu beef sukiyaki"
    },
    "Kyoto": {
        "Breakfast": "Warm Yudofu (silken tofu hot pot) with local green tea",
        "Lunch": "Traditional Kaiseki multi-course meal or matcha soba noodles",
        "Dinner": "Savory Okonomiyaki or local Kyoto-style vegetable tempura"
    },
    "Seoul": {
        "Breakfast": "Korean street toast with egg and hot barley tea",
        "Lunch": "Stone-pot Bibimbap with seasonal vegetables and gochujang",
        "Dinner": "Sizzling Korean BBQ beef bulgogi or spicy kimchi stew"
    },
    "Singapore": {
        "Breakfast": "Kaya Toast with soft-boiled eggs and local kopi",
        "Lunch": "Famous Hainanese Chicken Rice or spicy Laksa soup",
        "Dinner": "Savory Chilli Crab with fried mantou buns"
    },
    "Bali": {
        "Breakfast": "Fresh tropical fruit bowl with Balinese coffee",
        "Lunch": "Traditional Nasi Campur or crispy duck with sambal",
        "Dinner": "Suckling pig Babi Guling or seafood barbecue at Jimbaran Beach"
    },
    "Paris": {
        "Breakfast": "Warm butter croissant with cafe au lait",
        "Lunch": "Savory Croque Monsieur or classic French onion soup",
        "Dinner": "Coq au Vin or duck confit with a side of pommes frites"
    },
    "Rome": {
        "Breakfast": "Cornetto pastry with fresh cappuccino",
        "Lunch": "Classic Pasta Carbonara or thin-crust Roman pizza",
        "Dinner": "Tender Saltimbocca alla Romana followed by tiramisu"
    },
    "London": {
        "Breakfast": "Full English breakfast with eggs, sausages, beans, and tea",
        "Lunch": "Traditional pub-style Fish and Chips with mushy peas",
        "Dinner": "Savory Shepherd's Pie or classic Sunday Roast with Yorkshire pudding"
    },
    "Dubai": {
        "Breakfast": "Shakshuka with fresh flatbread and mint tea",
        "Lunch": "Chicken Shawarma wrap with garlic sauce and hummus",
        "Dinner": "Fragrant Lamb Ouzi with spiced rice and dates"
    },
    "New York": {
        "Breakfast": "Toasted bagel with lox and cream cheese, plus coffee",
        "Lunch": "New York-style thin-crust cheese slice or pastrami on rye",
        "Dinner": "Premium dry-aged strip steak or modern American fine dining"
    },
    "Sydney": {
        "Breakfast": "Smashed avocado toast on sourdough with flat white coffee",
        "Lunch": "Grilled barramundi fillet with garden salad",
        "Dinner": "Aussie-style barbecue ribs or fresh Sydney rock oysters"
    },
    "Cape Town": {
        "Breakfast": "Fresh rooibos tea with buttermilk rasks",
        "Lunch": "Traditional Bobotie spiced minced meat bake",
        "Dinner": "Grilled Kingklip fish or wood-fired Cape Malay chicken curry"
    },
    "Rio": {
        "Breakfast": "Pão de queijo (cheese bread) with fresh acai bowl",
        "Lunch": "Traditional Feijoada black bean and pork stew",
        "Dinner": "Churrascaria rodizio-style barbecued meats"
    },
    "Mumbai": {
        "Breakfast": "Spicy Vada Pav or Misal Pav with hot cutting chai",
        "Lunch": "Traditional Bombil fry (Bombay Duck) or Veg Kolhapuri thali",
        "Dinner": "Fragrant mutton biryani or butter chicken with garlic naan"
    },
    "Delhi": {
        "Breakfast": "Chole Bhature with spicy pickles and lassi",
        "Lunch": "Classic Butter Chicken with buttery naan from a local dhaba",
        "Dinner": "Assorted tandoori kebabs or rich Dal Makhani"
    },
    "Chennai": {
        "Breakfast": "Steamed Idli and Medu Vada with sambar and filter coffee",
        "Lunch": "Traditional South Indian meals served on banana leaf",
        "Dinner": "Spicy Chettinad Pepper Chicken or fish curry with parotta"
    },
    "Osaka": {
        "Breakfast": "Takoyaki octopus balls or local bakery pastries",
        "Lunch": "Savory Okonomiyaki cabbage pancake or Kushikatsu skewers",
        "Dinner": "Premium Kitsune Udon noodles or local beef shabu-shabu"
    },
    "Phuket": {
        "Breakfast": "Phuket style dim sum or roti with massaman curry",
        "Lunch": "Pad Thai with river prawns or spicy Tom Yum noodle soup",
        "Dinner": "Fresh grilled seafood by the beach or southern crab curry"
    },
    "Melbourne": {
        "Breakfast": "Sourdough toast with smashed avocado and specialty flat white",
        "Lunch": "Gourmet burger at a laneway cafe or authentic Italian pasta",
        "Dinner": "Australian steak with Shiraz wine or fusion Asian tasting menu"
    },
    "Reykjavik": {
        "Breakfast": "Skyr yogurt with local berries and rye bread toast",
        "Lunch": "Famous hot dog from Baejarins Beztu Pylsur or hot fish soup",
        "Dinner": "Slow-cooked Icelandic lamb shank or pan-seared fresh cod"
    },
    "Lima": {
        "Breakfast": "Pan con chicharron pork sandwich with sweet potato",
        "Lunch": "Fresh classic sea bass Ceviche with leche de tigre",
        "Dinner": "Lomo Saltado stir-fried beef with soy sauce, onions, and fries"
    },
    "Kullu": {
        "Breakfast": "Steamed local Siddu with hot ghee and red tea",
        "Lunch": "Traditional Himachali thali at a local dhaba",
        "Dinner": "Spiced trout fish roast or local legume stew with rice"
    },
    "Udaipur": {
        "Breakfast": "Poha Jalebi with hot milk tea from street vendors",
        "Lunch": "Mewari style dal baati churma thali in ghee",
        "Dinner": "Laal maas lamb curry with tandoori roti overlooking the lake"
    },
    "Varanasi": {
        "Breakfast": "Hot Kachori Sabzi followed by sweet crispy Jalebi at Ram Bhandar",
        "Lunch": "Traditional Banarasi Baati Chokha or regional thali served with ghee",
        "Dinner": "Spicy Tamatar Chaat and Golgappas at Deena Chaat Bhandar, finished with a sweet Banarasi Paan"
    },
    "Ayodhya": {
        "Breakfast": "Hot Bedmi Poori and Jalebi with Rabri from local sweet stalls",
        "Lunch": "Traditional Satvik thali cooked in pure ghee near Ram Janmabhoomi",
        "Dinner": "Local street foods like aloo tikki and sweet Ayodhya pedas"
    },
    "Gorakhpur": {
        "Breakfast": "Fluffy Poori Sabzi and sweet Lassi near Gorakhnath Temple",
        "Lunch": "Purvanchal style thali with dal, rice, and chokha at a local dhaba",
        "Dinner": "Local kebabs and biryani from historic city markets"
    },
    "Mirzapur": {
        "Breakfast": "Local kachori and hot tea in kulhad near Vindhyachal",
        "Lunch": "Traditional Purvanchali dal baati and spicy chutney",
        "Dinner": "Regional vegetable curry with roti and sweet Mirzapur pedas"
    },
    "Rishikesh": {
        "Breakfast": "Aloo poori with sweet lassi at a riverside joint",
        "Lunch": "Vegetarian Ayurvedic thali at an ashram cafe",
        "Dinner": "Local organic vegetable hotpot or tandoori paneer tikka"
    },
    "Shimla": {
        "Breakfast": "Hot buttered buns and chai at a heritage cafe",
        "Lunch": "Himachali Chha Gosht style curry with rice",
        "Dinner": "Warm vegetable stew and steamed momos from Mall Road"
    }
}

GENERIC_CLEAN_ATTRACTIONS = [
    "Historic Cathedral Square", "Art and Design Museum", "Harbor View Promenade", 
    "Coastal Lighthouse Lookout", "Old Quarter Craft Market", "Botanical Garden Greenhouse", 
    "Riverside Bistro Street", "Heritage Castle Ruins", "Modern Science Pavilion", 
    "Local Flea Market Lanes", "Summit Panoramic Deck", "Cultural Heritage Center", 
    "Downtown Boutique District", "Sunset Cruise Pier", "Old City Gate & Fort", 
    "Contemporary Art Gallery", "Central Park Conservatory", "Lakeside Walking Trail", 
    "Grand Opera Theater", "Traditional Food Alley", "Marine Life Aquarium", 
    "Panoramic Sky Observatory", "Scenic Gorge Walkway", "Local Artisans Workshop", 
    "Ancient Monastery Complex", "Waterfront Seafood Wharf", "Vintage Bazaar Street", 
    "Green Valley Overlook", "Town Hall Clock Tower", "National Memorial Park", 
    "Forest Nature Reserve", "Historic Bridge Walkway", "Sculpture Exhibition Garden", 
    "Local Farmers Pavilion", "Scenic Railway Station", "Hilltop Temple Steps", 
    "Downtown Arcade Walk", "Lighthouse Pier Cafe", "Ancient Burial Mounds", 
    "Wildlife Sanctuary Path", "Riverside Marina Deck", "Old Library Reading Room", 
    "Botanical Lily Pond Garden", "Sunset Beach Boardwalk", "Traditional Tea Pavilion", 
    "Historic Canal Cruise", "Panoramic Valley Overlook", "Arts & Crafts Square"
]
