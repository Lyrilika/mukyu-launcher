
pub struct PrintWork {
    pub name: &'static str,
    pub cover: &'static str,
    pub year: &'static str,
    pub author: &'static str,
    pub artist: &'static str,
}

pub const PRINTWORKS: &[PrintWork] = &[
    PrintWork { name: "Touhou Bunka Chou ~ Bohemian Archive in Japanese Red", cover: "bohemian_archive_in_japanese_red.jpg", year: "2005", author: "ZUN", artist: "Genji Asai, alphes, Chiha Ayami, Masato Takashina, Tateha, Touya, TOBI, Yuki Usagi, Tomoe Rokuwata" },
    PrintWork { name: "The Grimoire of Marisa", cover: "grimoire_of_marisa.jpg", year: "2009", author: "ZUN", artist: "Moriki Takeshi, Genji Asai" },
    PrintWork { name: "Alternative Facts in Eastern Utopia", cover: "alternative_facts_in_eastern_utopia.jpg", year: "2017", author: "ZUN", artist: "Aoi Kujira, Genji Asai, Aya Azuma, Toshira Arata, ALISON, Amamiya Tokuhisa, Suichuu Hanabi, TOKIAME, nyanya, Haniwa, Akio Hiiragi, Hitori, Masakichi, Mizutaki" },
    PrintWork { name: "The Grimoire of Usami", cover: "grimoire_of_usami.jpg", year: "2019", author: "ZUN", artist: "Aya Azuma, Genji Asai, Benishake(poprication)" },
    PrintWork { name: "Touhou Sangetsusei ~ Eastern and Little Nature Deity", cover: "eastern_little_nature_deity.jpg", year: "2005", author: "ZUN", artist: "Nemu Matsukura" },
    PrintWork { name: "Touhou Sangetsusei ~ Strange and Bright Nature Deity", cover: "strange_bright_nature_deity.jpg", year: "2006", author: "ZUN", artist: "Makoto Hirasaka" },
    PrintWork { name: "Touhou Sangetsusei ~ Oriental Sacred Place", cover: "oriental_sacred_place.jpg", year: "2009", author: "ZUN", artist: "Makoto Hirasaka" },
    PrintWork { name: "Touhou Sangetsusei ~ Visionary Fairies in Shrine", cover: "visionary_fairies_in_shrine.jpg", year: "2016", author: "ZUN", artist: "Makoto Hirasaka" },
    PrintWork { name: "Touhou Bougetsushou ~ Silent Sinner in Blue", cover: "silent_sinner_in_blue.jpg", year: "2007", author: "ZUN", artist: "Aki★Eda" },
    PrintWork { name: "Touhou Bougetsushou ~ Inaba of the Moon and Inaba of the Earth", cover: "inaba_moon_inaba_earth.jpg", year: "2007", author: "Toshihira Arata", artist: "Toshihira Arata" },
    PrintWork { name: "Touhou Ibarakasen ~ Wild and Horned Hermit", cover: "wild_horned_hermit.jpg", year: "2010", author: "ZUN", artist: "Aya Azuma" },
    PrintWork { name: "Touhou Suzunaan ~ Forbidden Scrollery", cover: "forbidden_scrollery.jpg", year: "2012", author: "ZUN", artist: "Moe Harukawa" },
    PrintWork { name: "Touhou Suichouka ~ Lotus Eaters (Ongoing)", cover: "lotuseaters.jpg", year: "2019", author: "ZUN", artist: "Mizutaki" },
    PrintWork { name: "Touhou Chireikiden ~ Foul Detective Satori (Ongoing)", cover: "foul_detective_satori.jpg", year: "2019", author: "ZUN", artist: "Ginmokusei, Akimaki Yuu" },
];

pub fn description(name: &str) -> &'static str {
    match name {
        "Touhou Sangetsusei ~ Eastern and Little Nature Deity" => "The story focuses on the daily lives of the Three Fairies of Light : Sunny Milk, Luna Child and Star Sapphire, said to be typical residents of Gensokyo.",
        "Touhou Sangetsusei ~ Strange and Bright Nature Deity" => "The story continues where Eastern and Little Nature Deity left off, it focuses on the daily lives of the Three Fairies of Light : Sunny Milk, Luna Child and Star Sapphire, said to be typical residents of Gensokyo.",
        "Touhou Bougetsushou ~ Silent Sinner in Blue" => "Silent Sinner in Blue follows the efforts of Reimu Hakurei, Marisa Kirisame, and the residents of the Scarlet Devil Mansion as they attempt to send a rocket to the moon, purportedly in order to invade the Lunar Capital. ",
        "Touhou Bougetsushou ~ Inaba of the Moon and Inaba of the Earth" => "A lighthearted spin-off following Reisen, Tewi, and the residents of Eientei. (not canonical to the Touhou Project)",
        "Touhou Sangetsusei ~ Oriental Sacred Place" => "The story continues where Strange and Bright Nature Deity left off, it focuses on the daily lives of the Three Fairies of Light : Sunny Milk, Luna Child and Star Sapphire, said to be typical residents of Gensokyo. ",
        "Touhou Ibarakasen ~ Wild and Horned Hermit" => "Kasen Ibaraki appears at the Hakurei Shrine one day, and immediately takes a liking to Reimu Hakurei and Marisa Kirisame, agreeing to help out around the shrine. Over the manga's nearly ten-year run, Kasen's inner thoughts around the direction and purpose of Gensokyo are expounded upon, as well as her own internal debates as to whether or not events from her own past should remain in the past, or be dealt with once and for all, as she joins Reimu and Marisa in their social gatherings and small adventures. ",
        "Touhou Suzunaan ~ Forbidden Scrollery" => "The plot follows Kosuzu Motoori, a cheerful and naive librarian, as the protagonist, as she goes about her daily life as the proprietor of her bookstore, Suzunaan. Throughout the story, she comes into contact with various demon books and otherwise old tomes from varying and unknown sources, leading to the slow reintroduction of traditional-style youkai into Gensokyo, juxtaposed with the relatively modern-minded and agreeable youkai typically seen in modern-day Gensokyo. Due to the various issues this causes, she attracts the attention of various incident solvers such as Reimu Hakurei, Marisa Kirisame, and Mamizou Futatsuiwa, as they attempt to investigate and sometimes contain the various youkai found in her mysterious demon books.",
        "Touhou Sangetsusei ~ Visionary Fairies in Shrine" => "The story takes place some times after Oriental Sacred Place, it focuses on the daily lives of the Three Fairies of Light : Sunny Milk, Luna Child and Star Sapphire, as well as their newfound fairy friend Clownpiece. ",
        "Touhou Suichouka ~ Lotus Eaters (Ongoing)" => "In the Human Village lies the bar Geidontei, where the zashiki-warashi Miyoi Okunoda works as a poster girl and waitress. The series revolves around her and the various mysteries and incidents surrounding her. After hours there is a small youkai-only get-together called the Sanshoku Geidontei (蚕喰鯢呑亭) with Suika Ibuki, Aya Shameimaru and Mamizou Futatsuiwa. ",
        "Touhou Chireikiden ~ Foul Detective Satori (Ongoing)" => "A most difficult case suddenly appears in Gensokyo. The usual incident resolvers are perplexed, so it's the job of the mind-reading youkai Satori to resolve this case!",
        "Touhou Kourindou ~ Curiosities of Lotus Asia" => "Stories centered around Kourindou, the antique shop between the human and youkai worlds.",
        "Touhou Bunka Chou ~ Bohemian Archive in Japanese Red" => "a collection of newspaper articles written by Aya Shameimaru.",
        "Touhou Gumonshiki ~ Perfect Memento in Strict Sense" => "An encyclopedia written by Hieda no Akyuu documenting Gensokyo's people, youkai, and history.",
        "The Grimoire of Marisa" => "spell card album of many characters with screen shots of that spell card from the games and comments written in the perspective of Marisa Kirisame.",
        "Touhou Gumonkuju ~ Symposium of Post-mysticism" => "A collection of discussions covering incidents, history, and supernatural topics.",
        "Alternative Facts in Eastern Utopia" => "Aya Shameimaru's attempt to create a tabloid magazine in the style of those from the Outside World, which she eventually cancelled and left unpublished. The book features in-universe articles, interviews and advertisements similar to the earlier Bohemian Archive in Japanese Red, but in a significantly more chaotic and haphazard format.",
        "The Grimoire of Usami" => "features a large selection of Spell Cards which are commented and judged by various characters during a firework festival.",
        "Strange Creators of Outer World" => "An official Touhou magazine supervised by ZUN featuring interviews, creator spotlights, comics, and information about Touhou works.",
        "Strange Articles of the Outer World" => "An official online magazine covering Touhou news, interviews, reviews, and related articles.",
        "Touhou Bougetsushou ~ Cage in Lunatic Runagate" => "The stand-alone stories in Cage in Lunatic Runagate offer detailed background information to the events in Silent Sinner in Blue, offering the insights and perspectives of various major and minor characters, and of those who didn't appear at all. ",
        "Whispered Oracle of Hakurei Shrine" => "Following the events of Unfinished Dream of All Living Ghost, Zanmu Nippaku approaches Reimu Hakurei to warn her that the youkai of Gensokyo would soon disappear. This was due to Chimata Tenkyuu releasing ownership of all land in Gensokyo, whose ownership was foundational to the existence of certain youkai. To help solidify their existence, Reimu, as well as some of the other humans in Gensokyo, created and sold omikuji slips based on the youkai they’d met.",
        _ => "No description available.",
    }
}

pub fn chapters(name: &str) -> Option<u32> {
    match name {
        "Touhou Sangetsusei ~ Eastern and Little Nature Deity" => Some(7),
        "Touhou Sangetsusei ~ Strange and Bright Nature Deity" => Some(25),
        "Touhou Sangetsusei ~ Oriental Sacred Place" => Some(18),
        "Touhou Sangetsusei ~ Visionary Fairies in Shrine" => Some(15),
        "Touhou Bougetsushou ~ Silent Sinner in Blue" => Some(21),
        "Touhou Bougetsushou ~ Inaba of the Moon and Inaba of the Earth" => Some(30),
        "Touhou Ibarakasen ~ Wild and Horned Hermit" => Some(51),
        "Touhou Suzunaan ~ Forbidden Scrollery" => Some(54),
        "Touhou Suichouka ~ Lotus Eaters (Ongoing)" => Some(81),
        "Touhou Chireikiden ~ Foul Detective Satori (Ongoing)" => Some(54),
        _ => None,
    }
}

pub fn archive_file(name: &str) -> Option<&'static str> {
    match name {
        "Touhou Sangetsusei ~ Eastern and Little Nature Deity" => Some("Eastern and Little Nature Deity.pdf"),
        "Touhou Sangetsusei ~ Strange and Bright Nature Deity" => Some("Strange and Bright Nature Deity.pdf"),
        "Touhou Sangetsusei ~ Oriental Sacred Place" => Some("Oriental Sacred Place.pdf"),
        "Touhou Sangetsusei ~ Visionary Fairies in Shrine" => Some("Visionary Fairies in Shrine.pdf"),
        "Touhou Bougetsushou ~ Silent Sinner in Blue" => Some("Silent Sinner in Blue.pdf"),
        "Touhou Bougetsushou ~ Inaba of the Moon and Inaba of the Earth" => Some("Inaba of the moon Inaba of the earth.pdf"),
        "Touhou Suzunaan ~ Forbidden Scrollery" => Some("Forbidden Scrollery.pdf"),
        "Touhou Suichouka ~ Lotus Eaters (Ongoing)" => Some("Lotus Eaters.pdf"),
        "Touhou Chireikiden ~ Foul Detective Satori (Ongoing)" => Some("Foul Detective Satori.pdf"),
        "Touhou Bunka Chou ~ Bohemian Archive in Japanese Red" => Some("Bohemian Archive in Japanese Red.pdf"),
        "The Grimoire of Marisa" => Some("The Grimoire of Marisa.pdf"),
        "The Grimoire of Usami" => Some("The Grimoire of Usami.pdf"),
        "Alternative Facts in Eastern Utopia" => Some("Alternative Facts in Eastern Utopia.pdf"),
        "Touhou Ibarakasen ~ Wild and Horned Hermit" => Some("Wild and Horned Hermit.pdf"),
        _ => None,
    }
}
