from typing import Dict, Any, Tuple
import hashlib
import random

# generation_config.py — Skin Realism v11 (Финальная версия)
# Уровень "фото со смартфона" — максимальный фотореализм с естественным светом
# + Auto‑Beauty 2.1: условная доработка лица (тон/текстура/цвет/лоб/родинки/каст) только при необходимости
#   — если аватар сгенерирован чисто и ровно, НИЧЕГО не правим.
# • Рефокус: глаза ВСЕГДА в зоне резкости (`focus_distance_lock="eyes"`)
# • Зерно и микро-рельеф сохранены, «воска» больше нет
# • Устранение жирной, восковой текстуры
# • Восстановление естественного светотеневого рисунка
# • Реалистичные контактные тени
# • Восстановление пористости и деталей
# Дата: 28 июля 2025
# Версия: Skin Realism v11 (финальная)
# -------------------------------------------------------------
#                  !! ️ФАЙЛ СГЕНЕРИРОВАН ИИ  !!
#   (ручные правки несложны, но сохраняйте v-контроль)
# -------------------------------------------------------------

#  ——— СТИЛИ АВАТАРОВ (ВСТРОЕНЫ В ФАЙЛ) ———
# === СТИЛИ АВАТАРОВ ИМПОРТИРУЮТСЯ ИЗ style.py ===
# Словари стилей удалены из этого файла и перенесены в style.py
# для лучшей организации кода

# === БАЗОВЫЕ ПРОМПТЫ (ОСНОВНЫЕ СТИЛИ) ===
# Промпты теперь импортируются из style.py

# -------------------------------------------------------------
# === ОСНОВНАЯ МОДЕЛЬ =========================================
# -------------------------------------------------------------
MULTI_LORA_MODEL = (
    "black-forest-labs/flux-1.1-pro"
)

CREATIVE_LORA_MODEL = (
    "lucataco/flux-dev-creative-lora:ae1f9e1da8e24c9686f3be8f2c8e9a1b2c3d4e5f6"
)

# -------------------------------------------------------------
# === ПРОФЕССИОНАЛЬНЫЙ НАБОР LoRA =============================
# -------------------------------------------------------------
HF_LORA_MODELS = [
    # Реализм
    "prithivMLmods/Flux-Realism-FineDetailed",
    "XLabs-AI/flux-RealismLora",
    "prithivMLmods/Canopus-LoRA-Flux-FaceRealism",
    "prithivMLmods/Flux-Natural-Skin-Texture",
    "EauDeNoire/Hands-XL-SD1.5-FLUX1-dev",
    "sczhou/SDXL-HandRefiner-v2",
    "KBlueLeaf/FiveFingerFix-SDXL",
    "XLabs-AI/flux-professional-photography",
    # Креатив
    "multimodalart/flux-lora-the-explorer",
    # Тело
    "username/flux-fullbody-realism",
]

# -------------------------------------------------------------
# === ГЛОБАЛЬНЫЕ ПАРАМЕТРЫ ====================================
# -------------------------------------------------------------
USER_AVATAR_LORA_STRENGTH = 0.72
MAX_LORA_COUNT = 6

# -------------------------------------------------------------
# === КОНФИГУРАЦИЯ LoRA =======================================
# -------------------------------------------------------------
LORA_CONFIG: Dict[str, Dict[str, Any]] = {
    "base_realism": {
        "model": "prithivMLmods/Flux-Realism-FineDetailed",
        "strength": 0.85,
        "keywords": ["realistic", "photographic", "natural", "authentic"],
        "priority": 1,
        "variations": ["super_realism", "ultra_realism"],
    },
    "face_ultra": {
        "model": "prithivMLmods/Canopus-LoRA-Flux-FaceRealism",
        "strength": 0.82,
        "keywords": ["face", "portrait", "detailed eyes"],
        "priority": 2,
        "variations": ["face_perfection"],
    },
    "skin_detail": {
        "model": "prithivMLmods/Flux-Natural-Skin-Texture",
        "strength": 0.78,
        "keywords": ["skin pores", "matte finish", "micro-variation", "subsurface scattering"],
        "priority": 3,
    },
    "skin_detail_soft": {
        "model": "prithivMLmods/Flux-Natural-Skin-Texture",
        "strength": 0.50,
        "keywords": ["soft skin texture", "beauty retouch"],
        "priority": 3,
    },
    "skin_realism_boost": {
        "model": "prithivMLmods/Flux-ExtraSkinRealism",
        "strength": 0.55,
        "keywords": ["skin pores", "realistic skin"],
        "priority": 3
    },
    "hands_ultra": {
        "model": "EauDeNoire/Hands-XL-SD1.5-FLUX1-dev",
        "strength": 0.92,
        "keywords": ["detailed hands"],
        "priority": 4,
    },
    "hands_precision": {
        "model": "sczhou/SDXL-HandRefiner-v2",
        "strength": 0.96,
        "keywords": ["hands_fix", "finger_anatomy", "accurate fingers"],
        "priority": 2,
    },
    "hands_five_fix": {
        "model": "KBlueLeaf/FiveFingerFix-SDXL",
        "strength": 0.92,
        "keywords": ["five_fingers", "finger_separation", "correct finger order"],
        "priority": 2,
    },
    "body_realism": {
        "model": "prithivMLmods/Flux-RealBody-XL-v1",
        "strength": 0.80,
        "keywords": ["full body", "torso", "legs", "natural posture"],
        "priority": 5,
    },
    "art_explorer": {
        "model": "multimodalart/flux-lora-the-explorer",
        "strength": 0.75,
        "keywords": ["painterly", "stylized"],
        "priority": 6,
    },
    "avatar_personal_lora": {
        "model": "username/flux-personal",
        "strength": USER_AVATAR_LORA_STRENGTH,
        "keywords": ["identity"],
        "priority": 0,
    },
    "super_realism": {"base": "base_realism", "strength_mod": 0.12},
    "ultra_realism": {"base": "base_realism", "strength_mod": 0.18},
    "face_perfection": {"base": "face_ultra", "strength_mod": 0.10},
    "hands_ultra_v2": {"base": "hands_ultra", "strength_mod": 0.06},
}
LORA_PRIORITIES = {k: v.get("priority", 99) for k, v in LORA_CONFIG.items()}

# -------------------------------------------------------------
# === ОБУЧЕНИЕ LoRA (DreamBooth) ==============================
# -------------------------------------------------------------
TRAINING_MODEL = (
    "ostris/flux-dev-lora-trainer:"
    "4ffd32160efd92e956d39c5338a9b8fbafca58e03f791f6d8011f3e20e8ea6fa"
)
TRAINING_CONFIG: Dict[str, Any] = {
    "resolution": 768,
    "train_batch_size": 4,
    "learning_rate": 3e-5,
    "lr_scheduler": "linear",
    "max_train_steps": 2500,
    "save_every_n_steps": 500,
    "mixed_precision": "fp16",
    "output_name": "username/flux-person-lora",
    "enable_identity_loss": True,
    "identity_loss_weight": 0.40,
}

# -------------------------------------------------------------
# === ТОКЕНЫ ДЕТАЛЕЙ / BEAUTY ================================
# -------------------------------------------------------------

NSFW_NEGATIVE = (
    "nude, naked, nude female, nude male, full nudity, exposed nipples, areola, "
    "genitals, pubic hair, cameltoe, underboob, sideboob, erotic, porn, sexual content, "
    "sex act, lactation, bondage, gratuitous cleavage, explicit, nsfw"
)

CARTOON_NEGATIVE = "toon shading, cel shading, smooth gradient skin, anime shading, stylised 3d, pixar render"
BODY_HAIR_NEGATIVE = (
    "armpit hair, leg hair, pubic hair, body hair stubble, chest hair on female, "
    "visible arm-pit hair, stubble on legs"
)
ENVIRONMENT_POSITIVE = (
    "photographic background detail, realistic depth cues, subtle atmospheric perspective, "
    "micro-detail on foliage and bark, soft ground contact shadows, volumetric light rays in dust"
)
HAIR_POSITIVE_TOKENS = (
    "individual hair strands, natural hair volume, subtle flyaway hairs, baby hair along hairline, "
    "realistic hairline transition, anisotropic highlights along strands, "
    "strand-level detail, sub-strand color variation, consistent natural hair color, "
    "detailed hair features, realistic hair lighting, natural hair shadows, "
    "proper hair focus, realistic hair proportions, natural hair color variation, "
    "authentic hair texture, realistic hair movement, natural hair interaction, "
    "detailed hair anatomy, realistic hair behavior, proper hair positioning"
)
HAIR_NEGATIVE_TOKENS = (
    "helmet hair, plastic hair, clumped strands, fake hairline, wig-like, "
    "unrealistic hair texture, cartoon hair, deformed hair, "
    "blurry hair details, unrealistic hair proportions, "
    "strange hair behavior, unrealistic hair placement, "
    "floating hair, hair clipping through skin, "
    "unrealistic hair lighting, unnatural hair shadows, "
    "inconsistent hair color, unrealistic hair movement, "
    "strange hair positioning, unrealistic hair interaction"
)

SKIN_POSITIVE_TOKENS = (
    "realistic skin texture, natural pores, subtle translucency, "
    "natural skin color, realistic skin lighting, authentic skin appearance, "
    "matte skin finish, visible pore detail, realistic skin specular breakup"
)
SKIN_NEGATIVE_TOKENS = (
    "plastic/waxy skin, doll-like skin, textureless skin, over-smoothed skin, oily shine, sweaty shine, "
    "waxy highlights, plastic highlights, airbrushed skin, poreless skin, "
    "blurred skin edges, gaussian-blur skin, beauty blur halo, deep philtrum groove, "
    "harsh philtrum shadow, over-defined cupid's bow, missing contact shadow, "
    "beauty blur mask, face smoothing halo, 3d toon shading, smooth gradient skin, Pixar-like skin, "
    "armpit hair, leg hair, body hair on women, "
    "greasy skin, oily skin, excessive shine, sweaty appearance, "
    "unnatural skin shine, plastic skin texture, artificial skin glow, "
    "strange facial features, unrealistic skin details, "
    "vague facial features, unclear facial details, "
    "blurry facial features, undefined facial details"
)

SKINTONE_POSITIVE = "skin-tone preserved, neutral white balance on skin, filmic color grade, gentle saturation, hue stability on skin"
SKINTONE_NEGATIVE = "blotchy red cheeks, strong blush patches, magenta hot spots on skin, cyan spill on skin, green spill on skin"

SPOTS_POSITIVE_TOKENS = "clean complexion, at most one or two tiny beauty marks, naturally placed"
SPOTS_NEGATIVE_TOKENS = "many moles on face, excessive moles, random dark facial spots, blotchy freckles clusters, acne spots"

SKIN_MICRO_GRAIN = "soft film grain 0.25, micro-variation in specular, tiny vellus hair on temples, dermal micro-capillaries, subtle vellus hair on temples"

BEAUTY_SKIN_POSITIVE = (
    "even skin tone, gentle under-eye softening, smooth nasolabial area, "
    "subtle diffusion on forehead, hydrated lips, youthful plumpness, "
    "subtle under-lip shadow, realistic philtrum shadow"
)
BEAUTY_SKIN_NEGATIVE = (
    "deep forehead lines, glabellar frown lines, pronounced nasolabial folds, "
    "marionette lines, crow's feet, under-eye bags, tear troughs, neck bands, "
    "chapped lips, blotchy redness, capillary flush, shadowed philtrum"
)

FOREHEAD_SMOOTH_POSITIVE = "relaxed brow, no forehead tension, smooth glabella region, subtle forehead texture, softened horizontal forehead micro-crease"
FOREHEAD_NEGATIVE_TOKENS = "forehead wrinkles, horizontal forehead creases, furrowed brow lines, elevated eyebrows lines"

COLOR_CAST_NEGATIVE = (
    "magenta skin cast, cyan skin cast, red/orange skin cast, neon tint on skin, "
    "sunburn patches, over-tanned skin, uneven blush, blotchy cheeks, "
    "green spill on skin, cyan spill on skin, foliage color bleed on skin, "
    "pool water color bleed on skin"
)
REDNESS_NEGATIVE = "rosacea, facial erythema, flushed cheeks, inflamed redness, excessive blush"

YOUTH_POSITIVE_TOKENS = "youthful appearance, subtle face lift effect, smooth jawline, soft cheek volume"
YOUTH_NEGATIVE_TOKENS = "visible aging signs, sagging skin, age spots"

MAKEUP_POSITIVE_TOKENS = "natural makeup, neutral blush minimal, soft contour, even complexion"
MAKEUP_NEGATIVE_TOKENS = "heavy blush, strong contouring, cakey foundation, overlined lips"

EYES_POSITIVE_TOKENS = (
    "tack-sharp pupils, crisp corneal highlight, asymmetric catchlights, "
    "realistic eyes, non-uniform iris pattern, moist tear line, "
    "sharp eyelashes, defined eyebrows, natural tear line highlight, "
    "direct eye contact with camera, engaged gaze, focused expression, "
    "realistic eye focus, natural eye direction, proper eye contact, "
    "detailed eye features, realistic eye expression, natural eye movement, "
    "eye priority focus, sharp eye details, realistic eye lighting, "
    "natural eye shadows, proper eye proportions, realistic eye color, "
    "detailed eye anatomy, natural eye behavior, realistic eye positioning"
)
EYES_NEGATIVE_TOKENS = (
    "soft-focus eyes, hazy pupils, mirrored catchlights, perfect symmetry in eyes, "
    "identical highlights, overly dark sclera, "
    "empty gaze, vacant stare, looking away from camera, "
    "unfocused eyes, distant gaze, absent expression, "
    "strange eye expression, unrealistic eye direction, "
    "vague eye details, unclear eye features, blurry eyes, "
    "blurry eye details, unrealistic eye lighting, unnatural eye shadows, "
    "inconsistent eye color, unrealistic eye proportions, "
    "cartoon eyes, unrealistic eye behavior, strange eye positioning, "
    "unrealistic eye focus, unnatural eye movement"
)

JEWELRY_POSITIVE_TOKENS = (
    "micro-scratches on metal, realistic metal specular, tiny contact shadow, "
    "proper jewelry fit, natural jewelry placement, realistic jewelry weight, "
    "subtle jewelry reflections, authentic jewelry texture, proper jewelry proportions, "
    "realistic jewelry shine, natural jewelry wear, authentic jewelry details, "
    "jewelry clasp detail, jewelry setting realistic, jewelry stone reflection, "
    "jewelry metal texture, realistic jewelry drape, jewelry layering natural, "
    "realistic jewelry size, natural jewelry color, detailed jewelry texture, "
    "proper jewelry focus, realistic jewelry lighting, natural jewelry shadows, "
    "authentic jewelry behavior, realistic jewelry interaction, proper jewelry positioning, "
    "detailed jewelry features, natural jewelry movement, realistic jewelry appearance"
)
JEWELRY_NEGATIVE_TOKENS = (
    "flat metal, fake reflections, oversized jewelry, floating jewelry, "
    "cartoon jewelry, plastic jewelry, unrealistic jewelry placement, "
    "jewelry clipping, jewelry artifacts, distorted jewelry, "
    "jewelry covering face, jewelry occlusion, jewelry glitch, "
    "jewelry floating, jewelry oversized, jewelry detail blurry, "
    "jewelry reflection fake, jewelry placement wrong, jewelry clipping, "
    "unrealistic jewelry size, deformed jewelry, cartoon jewelry appearance, "
    "blurry jewelry details, unrealistic jewelry proportions, "
    "strange jewelry behavior, unrealistic jewelry placement, "
    "floating jewelry, jewelry clipping through skin, "
    "unrealistic jewelry lighting, unnatural jewelry shadows, "
    "inconsistent jewelry color, unrealistic jewelry texture, "
    "strange jewelry positioning, unrealistic jewelry movement"
)

WATCH_POSITIVE_TOKENS = (
    "realistic watch strap, proper watch fit, watch clasp detail, "
    "watch face reflection, watch bezel detail, watch crown position, "
    "watch lugs connection, realistic watch weight, watch micro-indent on wrist"
)
WATCH_NEGATIVE_TOKENS = (
    "watch floating, watch oversized, watch face blurry, watch strap glitch, "
    "watch reflection fake, watch placement wrong, watch clipping"
)

RING_POSITIVE_TOKENS = (
    "proper ring fit, ring band detail, ring setting realistic, "
    "ring stone reflection, ring prongs detail, ring finger placement, "
    "ring metal texture, realistic ring proportions, natural ring indentation, "
    "realistic ring pressure, proper ring size, natural finger compression, "
    "authentic ring contact, realistic ring weight, natural ring placement"
)
RING_NEGATIVE_TOKENS = (
    "ring floating, ring oversized, ring finger wrong, ring setting blurry, "
    "ring reflection fake, ring placement wrong, ring clipping, "
    "ring too tight, ring indentation excessive, ring pressure unrealistic, "
    "ring finger deformation, ring finger swelling, ring finger discoloration, "
    "ring finger compression unrealistic, ring finger marks, ring finger damage"
)

NECKLACE_POSITIVE_TOKENS = (
    "necklace chain detail, necklace clasp realistic, necklace pendant detail, "
    "necklace layering natural, necklace length proper, necklace weight visible, "
    "necklace metal texture, realistic necklace drape"
)
NECKLACE_NEGATIVE_TOKENS = (
    "necklace floating, necklace oversized, necklace length wrong, necklace clasp blurry, "
    "necklace reflection fake, necklace placement wrong, necklace clipping"
)

EARRINGS_POSITIVE_TOKENS = (
    "earring post detail, earring back realistic, earring stone detail, "
    "earring metal texture, earring weight visible, earring placement natural, "
    "earring reflection subtle, realistic earring proportions"
)
EARRINGS_NEGATIVE_TOKENS = (
    "earrings floating, earrings oversized, earrings placement wrong, earrings detail blurry, "
    "earrings reflection fake, earrings clipping, earrings covering face"
)

BRACELET_POSITIVE_TOKENS = (
    "bracelet chain detail, bracelet clasp realistic, bracelet charm detail, "
    "bracelet fit proper, bracelet layering natural, bracelet weight visible, "
    "bracelet metal texture, realistic bracelet drape"
)
BRACELET_NEGATIVE_TOKENS = (
    "bracelet floating, bracelet oversized, bracelet fit wrong, bracelet detail blurry, "
    "bracelet reflection fake, bracelet placement wrong, bracelet clipping"
)

CROWN_TIARA_POSITIVE_TOKENS = (
    "crown gemstone detail, crown metalwork realistic, crown setting detail, "
    "crown fit proper, crown weight visible, crown reflection subtle, "
    "crown texture authentic, realistic crown proportions"
)
CROWN_TIARA_NEGATIVE_TOKENS = (
    "crown floating, crown oversized, crown fit wrong, crown detail blurry, "
    "crown reflection fake, crown placement wrong, crown clipping"
)

EXPRESSION_POSITIVE_TOKENS = "calm neutral expression, relaxed lips, subtle friendly look"
EXPRESSION_NEGATIVE_TOKENS = "awkward smile, asymmetric smirk, forced grin, mouth corner mismatch, perfect lip symmetry, overly uniform upper lip thickness, over-smooth cupid's bow"

GLASSES_KEYWORDS = ["glasses", "sunglasses", "очки", "солнечные очки"]
GLASSES_POSITIVE_TOKENS = (
    "glasses with two visible temple arms hugging head, proper refraction through lenses, "
    "tiny nose pad marks, soft contact shadow on nose and hair, slight hair displacement by temple arms, "
    "realistic metal/plastic specular, consistent frame size and bridge width across shots"
)
GLASSES_NEGATIVE_TOKENS = (
    "missing temple arms, floating glasses, lens with no refraction, "
    "glasses clipping into hair or head, wrong perspective of frames, fake reflections, "
    "oversized frames, undersized frames, inconsistent frame size between shots"
)

GLASSES_RULES: Dict[str, Any] = {
    "bridge_ratio_min": 0.90,
    "bridge_ratio_max": 1.15,
    "require_two_temple_arms": True,
    "require_refraction": True,
    "size_jitter_limit": 0.05,
}

PIERCING_KEYWORDS = ["piercing", "nose ring", "nose stud", "septum", "пирсинг", "украшение", "серёжка", "кольцо в носу"]
PIERCING_POSITIVE_TOKENS = (
    "accurate piercing placement on left nostril, polished surgical steel, "
    "small specular highlight, soft contact shadow on skin, realistic metal roughness, 2mm stud"
)
PIERCING_NEGATIVE_TOKENS = (
    "floating piercing, duplicated piercing, misaligned piercing, matte metal, "
    "piercing clipping, wrong side piercing, oversized piercing"
)

FABRIC_POSITIVE_TOKENS = (
    "natural fabric micro-wrinkles, thread-level detail, tactile ribbed knit, "
    "strap indentation on skin, compression wrinkles around knots, "
    "realistic fabric texture, natural fabric drape, proper fabric fit, "
    "detailed fabric patterns, realistic fabric lighting, natural fabric shadows, "
    "proper clothing proportions, realistic clothing size, natural clothing behavior, "
    "detailed clothing details, realistic clothing interaction, natural clothing weight"
)
FABRIC_NEGATIVE_TOKENS = (
    "plastic fabric, melted folds, strap floating, strap with no indentation, "
    "unrealistic clothing size, deformed clothing, cartoon clothing, "
    "blurry clothing details, unrealistic clothing proportions, "
    "strange clothing behavior, unrealistic clothing placement, "
    "floating clothing, clothing clipping through body"
)

DOF_POSITIVE_TOKENS = (
    "natural lens bokeh, shallow depth of field, gentle optical vignetting, "
    "non-uniform bokeh shapes on water, foreground edge protection, "
    "subtle background detail, bark micro-texture, realistic foliage variation, "
    "realistic background, natural background lighting, proper background focus, "
    "detailed background texture, natural background color, realistic background behavior, "
    "proper background proportions, natural background shadows, realistic background details, "
    "beautiful background, natural background movement, realistic background interaction"
)
BOKEH_NEGATIVE_TOKENS = (
    "uniform bokeh, repeating bokeh shapes on water, tiled highlights, "
    "unrealistic background, cartoon background, artificial background, "
    "blurry background details, unrealistic background lighting, "
    "unnatural background color, strange background behavior, "
    "unrealistic background proportions, unnatural background shadows, "
    "inconsistent background texture, unrealistic background movement"
)

PRO_COMPOSITION_POSITIVE = (
    "rule of thirds framing, balanced headroom, proper lead room, "
    "intentional negative space, no joint crop"
)

TEETH_POSITIVE_TOKENS = (
    "natural individual teeth, slight translucency at edges, subtle gum line, varied tooth size, "
    "soft shadow between teeth, realistic occlusion"
)
TEETH_NEGATIVE_TOKENS = "plastic teeth, single block teeth, overwhite teeth, fake gum line, fused teeth"
SMILE_KEYWORDS = ["smile", "улыб", "grin"]

HAND_KEYWORDS = [
    "hand", "hands", "рук", "руки", "ладон", "finger",
    "palm", "grip", "grasp", "holding", "touch", "gesture",
    "ладонь", "держит", "сжимает", "касается", "жест",
    "обнимает", "охватывает", "столб", "ствол", "pole", "branch", "bamboo"
]
HAND_POSITIVE_TOKENS = (
    "accurate hand anatomy, separated fingers, natural finger curvature, realistic fingernails, "
    "correct wrist alignment, visible knuckle folds, soft shadow between fingers, "
    "nail bed separation, proper nail curvature, realistic palmar pads, "
    "correct thumb opposition, natural tendon definition on back of hand, "
    "compression of soft tissue on contact, subtle wrinkles at MCP/PIP joints, "
    "subtle dorsal vein, slight palmar crease, micro callus detail on palm pads, "
    "natural hand proportions, realistic finger length, proper hand positioning, "
    "natural hand gestures, relaxed hand pose, realistic hand anatomy, "
    "exactly five fingers per hand, natural finger spacing, realistic finger thickness, "
    "proper finger joints, natural finger movement, realistic hand proportions, "
    "natural hand size relative to body, realistic finger nail shape, "
    "consistent manicure across all fingers, natural finger color, "
    "realistic finger shadows, natural finger lighting, proper finger focus, "
    "natural hand gestures, realistic finger movements, proper hand positioning, "
    "realistic hand behavior, natural hand expressions, proper hand focus, "
    "detailed hand features, realistic hand texture, natural hand color, "
    "authentic hand movements, realistic hand interaction, proper hand anatomy, "
    "photorealistic hand rendering, realistic hand photography, natural hand capture, "
    "authentic hand photograph, real hand photography, natural hand lighting, "
    "compression of soft tissue on contact, nail bed separation, micro palmar wrinkles, finger pad flattening"
)
HAND_NEGATIVE_TOKENS = (
    "fused fingers, extra fingers, missing fingers, distorted wrists, deformed hands, "
    "melted fingers, duplicate thumbs, floating fingers, rigid finger curvature, "
    "uniform finger thickness, overstretched thumb, paper-thin palm, missing knuckle folds, "
    "mismatched finger lengths, broken wrist bend, reversed finger joints, "
    "smeared or merged nails, nails fused with skin, duplicated nails, "
    "finger tips melted, palm intersecting object, hand clipping through object, "
    "arm clipping, disconnected limb, poorly drawn hands, bad hands, bad_hand, bad hand anatomy, "
    "overlapping fingers, duplicated limb, disconnected limb, wrong finger joint, "
    "janky hand pose, mutant hand, surreal hand, elongated fingers, "
    "extra digit, extra arm, extra limb growth, deformed fingernails, "
    "unnatural hand poses, stiff hand gestures, unrealistic hand positioning, "
    "hand covering face, hand blocking eyes, hand obscuring features, "
    "more than five fingers, less than five fingers, chaotic finger arrangement, "
    "unnatural finger bends, unrealistic finger proportions, "
    "darkened fingers, discolored fingers, inconsistent finger color, "
    "rings on ring finger, rings on wrong fingers, multiple rings on same finger, "
    "inconsistent manicure, different nail colors, mismatched nail shapes, "
    "unnatural finger shadows, unrealistic finger lighting, "
    "thick neck, neck folds, unnatural neck wrinkles, "
    "unrealistic body proportions, distorted limbs, disproportionate body parts, "
    "cartoon hands, cartoon fingers, unrealistic hand behavior, "
    "strange finger movements, unrealistic finger gestures, "
    "awkward hand gestures, unnatural hand poses, "
    "stiff hand movements, unrealistic hand behavior, "
    "strange hand expressions, unnatural hand positioning, "
    "cartoon hand gestures, unrealistic hand interaction, "
    "unnatural hand anatomy, deformed hand movements, "
    "cartoon hand rendering, anime hand rendering, 3D hand rendering, CGI hand look, "
    "plastic hand rendering, artificial hand rendering, synthetic hand rendering, "
    "unrealistic hand rendering, fake hand rendering, artificial hand appearance, "
    "extra fingers, missing fingers, fused fingers, deformed fingers, unnatural finger count, incorrect finger anatomy, "
    "four fingers, missing index finger, missing ring finger, "
    "index finger same length as ring finger, wrong finger order"
)

POSE_POSITIVE_TOKENS = (
    "natural relaxed posture, shoulders level and relaxed, neutral head position, "
    "natural neck curvature, frontal head orientation, confident stance, "
    "natural arm positioning, relaxed hands, natural body language, "
    "realistic pose variety, natural weight distribution, comfortable positioning, "
    "gentle head tilt under 8 degrees, head turn under 10 degrees, "
    "realistic clavicle elevation with raised arm, deltoid shoulder step, "
    "natural shoulder slope, proper posture, relaxed muscles, "
    "direct eye contact with camera, engaged gaze, focused expression"
)
POSE_NEGATIVE_TOKENS = (
    "back view, over-the-shoulder back view, subject turned away from camera, "
    "profile view, side view looking away, extreme neck twist, elongated neck, "
    "over-rotated head (>15°), heavy head tilt (>15°), "
    "hyperextended wrist, elbows bending backwards, shoulder dislocation"
)
POSE_GUIDE = "three-quarter head turn, gentle S-curve posture, relaxed shoulders, chin slightly down, engaged eyes"
POSE_SAFETY_POSITIVE = "frontal or slight three-quarter view, minimal head rotation 0-10°, minimal head tilt, stable perspective"

IDENTITY_POSITIVE_TOKENS = (
    "preserve identity, consistent facial geometry, same person as reference, "
    "stable facial structure, matching nose/eyes/lips proportions, consistent hair color"
)
IDENTITY_NEGATIVE_TOKENS = "different person, altered identity, face swap, mismatched facial features, identity drift"
IDENTITY_STRONG_POSITIVE = (
    "preserve identity strictly, consistent jaw and cheek volume, stable nose bridge and alar width, "
    "stable philtrum depth mild, consistent lip volume and cupid's bow, consistent eyebrow thickness and hairline"
)
IDENTITY_STRONG_NEGATIVE = (
    "identity drift, different person, altered jawline, changed nose width, changed lip shape, "
    "mismatched eyebrow thickness, mismatched hairline"
)

CLAVICLE_POSITIVE_TOKENS = (
    "visible collarbones, natural clavicle definition, realistic shoulder anatomy, "
    "proper clavicle prominence, natural shoulder slope, realistic bone structure, "
    "subtle clavicle shadow, natural shoulder width, realistic upper torso, "
    "natural clavicle curve, proper shoulder alignment, detailed clavicle features, "
    "realistic clavicle lighting, natural clavicle shadows, authentic clavicle behavior, "
    "realistic clavicle interaction, proper clavicle positioning, detailed clavicle texture, "
    "natural clavicle color, authentic clavicle appearance, realistic clavicle movement"
)
CLAVICLE_NEGATIVE_TOKENS = (
    "invisible collarbones, missing clavicle definition, flat shoulders, "
    "unnatural shoulder width, distorted clavicle, unrealistic bone structure, "
    "missing collarbones, deformed collarbones, unnatural collarbone structure, invisible collarbones"
)

FORBIDDEN_ELEMENTS_NEGATIVE = (
    "nudity, topless, underwear, lingerie, swimsuit, bikini, revealing clothing, "
    "exposed skin, cleavage, "
    "short skirts, short shorts, tight clothing, see-through clothing, "
    "suggestive poses, provocative gestures, seductive expressions, "
    "bedroom poses, intimate settings, romantic scenes, "
    "alcohol, cigarettes, drugs, smoking, drinking, party scenes, "
    "violence, weapons, guns, knives, blood, injuries, scars, "
    "tattoos, body modifications, extreme makeup, "
    "unrealistic body proportions, overly thin, overly muscular, "
    "cartoon style, anime style, fantasy creatures, mythical beings, "
    "hairy armpits, body hair, excessive body hair, unshaven, "
    "hunched posture, slouching, poor posture, rounded shoulders, "
    "unrealistic wrinkles, excessive wrinkles, unnatural skin folds, "
    "extra limbs, extra arms, extra legs, extra hands, extra feet, "
    "missing limbs, missing arms, missing legs, missing hands, missing feet, "
    "deformed limbs, deformed arms, deformed legs, deformed hands, deformed feet, "
    "floating limbs, disconnected limbs, broken limbs, "
    "extra body parts, extra heads, extra faces, extra eyes, extra mouths, "
    "missing body parts, missing heads, missing faces, missing eyes, missing mouths, "
    "deformed body parts, deformed heads, deformed faces, deformed eyes, deformed mouths, "
    "cartoon rendering, anime rendering, 3D rendering, CGI look, "
    "plastic rendering, artificial rendering, synthetic rendering, "
    "unrealistic rendering, fake rendering, artificial appearance, "
    "topless female, topless male, bikini_top_removed, thong_only, g-string, "
    "side-boob, under-boob, t-back, erotic lingerie"
)

ANIMAL_KEYWORDS = ["cat", "dog", "kitten", "puppy", "animal", "pet", "кошка", "кот", "котик", "собака", "пёс", "пес", "щенок"]
ANIMAL_POSITIVE_TOKENS = (
    "accurate animal anatomy, correct paw structure, separated toes, proper paw pads, believable claws, "
    "realistic animal proportions, natural animal behavior, realistic animal size, "
    "detailed animal fur, natural animal expression, realistic animal pose, "
    "proper animal focus, realistic animal details, natural animal lighting, "
    "realistic animal texture, natural animal color, detailed animal features"
)
ANIMAL_NEGATIVE_TOKENS = (
    "extra toes, fused paw, deformed paws, human-like fingers on animals, missing paw pads, "
    "unrealistic animal size, cartoon animals, deformed animals, "
    "blurry animal details, unrealistic animal proportions, "
    "strange animal behavior, unrealistic animal pose"
)
ANIMAL_CONTACT_POSITIVE = "soft fur compression under fingers, tiny shadow at paw contact, realistic animal interaction"

OBJECT_POSITIVE_TOKENS = (
    "realistic object size, proper object proportions, natural object placement, "
    "detailed object texture, realistic object lighting, natural object behavior, "
    "proper object focus, realistic object details, natural object interaction, "
    "realistic object weight, natural object shadows, detailed object features"
)

PHOTOREALISTIC_POSITIVE_TOKENS = (
    "photorealistic rendering, realistic photography, natural camera capture, "
    "authentic photograph, real photography, natural lighting, "
    "realistic depth of field, natural bokeh, authentic camera lens, "
    "realistic film grain, natural color grading, authentic photographic style"
)

FLAG_POSITIVE_TOKENS = (
    "Russian flag, Chinese flag, Korean flag, Japanese flag, "
    "CIS country flags, Kazakhstan flag, Belarus flag, Armenia flag, "
    "Azerbaijan flag, Kyrgyzstan flag, Tajikistan flag, Turkmenistan flag, "
    "Uzbekistan flag, Moldova flag, Georgia flag, realistic flag proportions, "
    "proper flag colors, authentic flag design, natural flag movement"
)
FLAG_NEGATIVE_TOKENS = (
    "deformed flags, unrealistic flag colors, cartoon flags, "
    "floating flags, unrealistic flag movement, wrong flag proportions"
)
OBJECT_NEGATIVE_TOKENS = (
    "unrealistic object size, deformed objects, cartoon objects, "
    "blurry object details, unrealistic object proportions, "
    "strange object behavior, unrealistic object placement, "
    "floating objects, objects clipping through surfaces"
)

BODY_KEYWORDS = ["body", "torso", "legs", "full body", "silhouette", "shoulders"]
BODY_POSITIVE_TOKENS = (
    "natural body proportions, correct anatomy, realistic muscle tone, balanced posture, "
    "natural spine curvature, clavicle definition, scapula hints under skin, "
    "realistic body proportions, natural limb proportions, proper head-to-body ratio, "
    "realistic arm length, natural leg proportions, proper hand-to-arm ratio, "
    "natural neck proportions, realistic shoulder width, proper torso proportions, "
    "realistic body focus, natural body lighting, proper body shadows, "
    "realistic body texture, natural body color, detailed body features, "
    "natural body movement, realistic body behavior, proper body positioning"
)
BODY_NEGATIVE_TOKENS = (
    "distorted torso, skinny legs, unnatural proportions, deformed posture, wobbling hips, "
    "unrealistic body proportions, disproportionate limbs, wrong head-to-body ratio, "
    "unnatural arm length, unrealistic leg proportions, wrong hand-to-arm ratio, "
    "thick neck, neck folds, unnatural neck wrinkles, unrealistic neck proportions, "
    "cartoon body, unrealistic body behavior, strange body movements, "
    "unrealistic body lighting, unnatural body shadows, inconsistent body color, "
    "distorted body parts, unrealistic body texture, strange body positioning, "
    "duplicate limbs, cloned body parts, multiple heads, extra body parts, missing body parts, deformed body parts"
)

BEACH_KEYWORDS = ["beach", "coast", "sea", "ocean", "shore", "pool", "resort", "пляж", "море", "океан", "берег", "бассейн", "sunny", "полдень"]
NEON_KEYWORDS = ["neon", "cyberpunk", "night city", "city lights", "cockpit", "кабина", "иллюминатор", "неон", "ночной", "вывески"]
LEAF_KEYWORDS = ["leaf", "leaves", "palm", "frond", "foliage", "листья", "лист", "пальма", "пальмы"]

OCCLUSION_EDGE_NEGATIVE = (
    "object-skin intersection, sticker-like hair edges, hair halo, missing contact shadow, "
    "hair crossing clothing with no shadow, strap floating, strap with no indentation"
)

TREE_POSE_NEGATIVE = (
    "awkward tree pose, hugging a tree, hugging a pole, two hands fully wrapped around trunk, "
    "arm behind head while touching tree, forearm parallel to trunk, palm flat on trunk without knuckle bend"
)
FACE_OCCLUSION_NEGATIVE = "leaf crossing face or eyes, foliage blocking face, object tangent to facial outline"
HAND_SCALE_NEGATIVE = "undersized hands near face, oversized hands near face"

FACE_CLEAR_POSITIVE = "clear space around facial contour, no object tangent to face, foliage kept off face"
SAFE_HAND_POSE_POSITIVE = "relaxed arms, one hand on hip (thumb forward), gentle finger splay"
CONTACT_PHYSICS_POSITIVE = "micro indentation at grip points, micro contact shadow around fingers and straps, soft lip indentation, finger pad flattening"

# -------------------------------------------------------------
# === NEGATIVE PROMPTS ========================================
# -------------------------------------------------------------
NEGATIVE_BLOCK_BASE = "low quality, blurry, distorted, watermark, jpeg artifacts"
NEGATIVE_BLOCK_BASE += (", " + NSFW_NEGATIVE + ", " + BODY_HAIR_NEGATIVE)
NEGATIVE_BLOCK_CREATIVE = "low quality, blurry, watermark, text, logo"

CARTOON_NEG = (
    "anime, manga, cartoon, cel shading, toon shading, pixar, disney, illustration, "
    "flat 3d, smooth gradient skin, 3d render, cgi"
)

NUDITY_NEG = "nude, naked, nsfw, exposed genitals, exposed nipples, explicit, erotic, suggestive, sexual content"

FACE_DIRT_NEGATIVE = "dirty face, grime on skin, makeup smudges, patchy foundation"

NEGATIVE_PROMPTS: Dict[str, str] = {
    "default": (
        "low quality, bad quality, worst quality, blurry, pixelated, noisy, distorted, "
        "deformed, mutated, ugly, bad anatomy, bad proportions, extra limbs, missing limbs, "
        "extra hands, extra fingers, missing fingers, fused fingers, deformed hands, unrealistic hands, "
        "duplicate limb, extra arms, extra legs, floating limb, "
        "bad face, distorted face, unrealistic behavior, unnatural poses, awkward poses, "
        "watermark, text, logo, signature, username, artist name, "
        "3d render, cartoon, anime, sketch, drawing, painting, artistic, illustration, "
        "cgi, fake, artificial, plastic skin, doll skin, unrealistic, overexposed, underexposed, "
        "duplicate body parts, cloned avatar, multiple heads, extra limbs, extra arms, extra legs, extra hands, extra feet, extra fingers, missing fingers, fused fingers, deformed hands, unrealistic hands, disproportionate body parts, unnatural body proportions, incorrect anatomy, distorted torso, skinny legs, unnatural proportions, deformed posture, wobbling hips, unrealistic body proportions, disproportionate limbs, wrong head-to-body ratio, unnatural arm length, unrealistic leg proportions, wrong hand-to-arm ratio, thick neck, neck folds, unnatural neck wrinkles, unrealistic neck proportions, cartoon body, unrealistic body behavior, strange body movements, unrealistic body lighting, unnatural body shadows, inconsistent body color, distorted body parts, unrealistic body texture, strange body positioning"
    ),
    "ultra_realistic_max": (
        "bad quality, blurry, extra fingers, fused fingers, plastic skin, waxy, "
        "cartoon, anime, cgi, bad anatomy, harsh cast, redness, oily, "
        "deformed, mutated, extra limbs, missing limbs, "
        "unrealistic behavior, unnatural poses, awkward poses, "
        "watermark, text, logo, signature, "
        "oversaturated, artificial lighting, overexposed, underexposed, "
        "uneven lighting, color noise, over-sharpened edges, "
        "waxy forehead, over-smooth face, no contact shadows, "
        "plastic lips, sticky gloss effect, wax lips, "
        "plastic skin, wax lips, perfect lip symmetry, overly smooth face, no shadow under nose, "
        "gloss lips, filtered skin, oily forehead, doll skin, blurry skin detail, smudged specular, "
        "overfiltered skin tone, skin reflection, doll face, oil gloss, no texture, baby fat face, "
        "overexposed cheeks, blurry chin, plastic skin, oily skin, wax lips, overly smooth cheeks, "
        "perfect lip symmetry, face blur, no skin texture, poreless face, glow forehead, "
        "CGI texture, AI skin blur, mirrored face, lip gloss, mirrored lips, AI-rendered lip symmetry, "
        "overly smooth skin, filtered face, oily skin, excessive retouching, airbrushed cheeks, "
        "glossy face, filtered look, perfect symmetry, beauty filter effect, no pores, "
        "skin shine, overexposed skin highlights, "
        "oily skin, glossy forehead, blurred skin texture, overprocessed skin, "
        "waxy skin, perfect lip symmetry, gloss lips, no pores, flat face, "
        "artificial skin tone, wax lips, porcelain skin, fake texture, "
        "duplicate body parts, cloned avatar, multiple heads, extra limbs, extra arms, extra legs, extra hands, extra feet, extra fingers, missing fingers, fused fingers, deformed hands, unrealistic hands, disproportionate body parts, unnatural body proportions, incorrect anatomy, distorted torso, skinny legs, unnatural proportions, deformed posture, wobbling hips, unrealistic body proportions, disproportionate limbs, wrong head-to-body ratio, unnatural arm length, unrealistic leg proportions, wrong hand-to-arm ratio, thick neck, neck folds, unnatural neck wrinkles, unrealistic neck proportions, cartoon body, unrealistic body behavior, strange body movements, unrealistic body lighting, unnatural body shadows, inconsistent body color, distorted body parts, unrealistic body texture, strange body positioning"
    ),
    "creative_max": (
        NEGATIVE_BLOCK_CREATIVE + ", duplicate body parts, cloned avatar, multiple heads, extra limbs, extra arms, extra legs, extra hands, extra feet, extra fingers, missing fingers, fused fingers, deformed hands, unrealistic hands, disproportionate body parts, unnatural body proportions, incorrect anatomy, distorted torso, skinny legs, unnatural proportions, deformed posture, wobbling hips, unrealistic body proportions, disproportionate limbs, wrong head-to-body ratio, unnatural arm length, unrealistic leg proportions, wrong hand-to-arm ratio, thick neck, neck folds, unnatural neck wrinkles, unrealistic neck proportions, cartoon body, unrealistic body behavior, strange body movements, unrealistic body lighting, unnatural body shadows, inconsistent body color, distorted body parts, unrealistic body texture, strange body positioning"
    ),
}

# -------------------------------------------------------------
# === CAMERA SHOTS ============================================
# -------------------------------------------------------------
CAMERA_SHOTS: Dict[str, Dict[str, Any]] = {
    "extreme_close_up": {"description": "Сверхкрупный план", "keywords": ["eyes", "detail"], "weight": 0.14},
    "close_up": {"description": "Крупный план", "keywords": ["face", "portrait"], "weight": 0.32},
    "medium_shot": {"description": "Средний план", "keywords": ["upper body"], "weight": 0.24},
    "waist_shot": {"description": "Поясной план", "keywords": ["waist", "mid body"], "weight": 0.17},
    "full_shot": {"description": "Общий план", "keywords": ["full body"], "weight": 0.14},
    "long_shot": {"description": "Дальний план", "keywords": ["environment"], "weight": 0.09},
    "low_angle": {"description": "Низкий угол силы", "keywords": ["power", "low angle"], "weight": 0.06},
    "high_angle": {"description": "Верхний ракурс", "keywords": ["high angle", "bird view"], "weight": 0.05},
    "over_shoulder": {"description": "Через плечо (OTS)", "keywords": ["ots", "over shoulder"], "weight": 0.05},
    "dutch_angle": {"description": "Наклонный угол", "keywords": ["dynamic"], "weight": 0.00},
    "50mm_shot": {"description": "Широкий портрет", "keywords": ["wide portrait"], "weight": 0.10},
    "135mm_shot": {"description": "Теле-портрет", "keywords": ["tele portrait"], "weight": 0.10},
}

# -------------------------------------------------------------
# === КАМЕРА / СВЕТ ===========================================
# -------------------------------------------------------------
CAMERA_SETUP_BASE = "Professional DSLR, 85mm lens, f/1.8 aperture, natural lighting, sharp focus, high resolution"
CAMERA_SETUP_HAIR = f"{CAMERA_SETUP_BASE}, {HAIR_POSITIVE_TOKENS}"
CAMERA_SETUP_BEAUTY = (
    "DSLR 85mm lens, f/2.0, natural lighting from window, soft falloff, "
    "Rembrandt fill, balanced highlights, subtle cheek shadows, "
    "realistic bounce from white wall"
)
LUXURY_DETAILS_BASE = "Natural matte skin with pores, subtle imperfections, authentic physique"

# -------------------------------------------------------------
# === ASPECT RATIOS ===========================================
# -------------------------------------------------------------
ASPECT_RATIOS: Dict[str, Tuple[int, int]] = {
    "1:1": (1408, 1408), "3:4": (1080, 1440), "4:3": (1440, 1080),
    "9:16": (810, 1440), "16:9": (1440, 810), "2:3": (960, 1440),
    "3:2": (1440, 960), "5:4": (1152, 1440), "4:5": (1080, 1350),
}

def get_resolution_by_ratio(name: str) -> Tuple[int, int]:
    return ASPECT_RATIOS.get(name, (1408, 1408))

def choose_model_by_style(style_key: str) -> str:
    if is_creative_style(style_key):
        return "flux-creative"
    else:
        return "flux-trained"

# -------------------------------------------------------------
# === ЦЕНТРАЛИЗОВАННАЯ КОНФИГУРАЦИЯ ЦЕН =====================
# -------------------------------------------------------------
USER_PRICES = {
    "image_generation": {
        "with_avatar": 2,
        "photo_to_photo": 2,
        "default": 1,
    },
    "video_generation": {
        "ai_video_v2_1": 20,
    },
    "avatar_training": {
        "train_flux": 5,
    },
    "prompt_assistance": {
        "prompt_assist": 1,
    }
}

def get_image_generation_cost(generation_type: str, num_outputs: int = 2) -> int:
    if generation_type == 'with_avatar':
        return USER_PRICES["image_generation"]["with_avatar"]
    elif generation_type == 'photo_to_photo':
        return USER_PRICES["image_generation"]["photo_to_photo"]
    else:
        return USER_PRICES["image_generation"]["default"]

def get_video_generation_cost(generation_type: str) -> int:
    return USER_PRICES["video_generation"].get(generation_type, 20)

def get_avatar_training_cost(generation_type: str) -> int:
    return USER_PRICES["avatar_training"].get(generation_type, 5)

def get_prompt_assistance_cost(generation_type: str) -> int:
    return USER_PRICES["prompt_assistance"].get(generation_type, 1)

def get_generation_cost(generation_type: str, num_outputs: int = 2) -> int:
    if generation_type in USER_PRICES["video_generation"]:
        return get_video_generation_cost(generation_type)
    elif generation_type in USER_PRICES["avatar_training"]:
        return get_avatar_training_cost(generation_type)
    elif generation_type in USER_PRICES["prompt_assistance"]:
        return get_prompt_assistance_cost(generation_type)
    else:
        return get_image_generation_cost(generation_type, num_outputs)

# -------------------------------------------------------------
# === МОДЕЛИ ГЕНЕРАЦИИ ========================================
# -------------------------------------------------------------
IMAGE_GENERATION_MODELS: Dict[str, Dict[str, Any]] = {
    "flux-trained": {
        "name": "✨ Генерация с аватаром / Фото-референс",
        "id": MULTI_LORA_MODEL,
        "api": "replicate",
        "max_quality": True,
        "optimal_resolution": (1408, 1408),
        "supports_ultra_realism": True,
    },
    "flux-creative": {
        "name": "🎨 Генерация Art / Sketch",
        "id": CREATIVE_LORA_MODEL,
        "api": "replicate",
        "max_quality": True,
        "optimal_resolution": (1408, 1408),
    },
    "flux-person-lora": {
        "name": "📸 AI-фотосессия на вашем лице",
        "id": TRAINING_CONFIG["output_name"],
        "api": "replicate",
        "max_quality": True,
        "optimal_resolution": (1408, 1408),
    },
    "flux-trainer": {
        "name": "🛠 Обучение аватара",
        "id": TRAINING_MODEL,
        "api": "replicate",
    },
    "kwaivgi/kling-v2.1": {
        "name": "🎥 AI-видео (Kling 2.1)",
        "id": "kwaivgi/kling-v2.1",
        "api": "replicate",
        "cost": get_video_generation_cost("ai_video_v2_1"),
    },
    "meta-llama-3-8b-instruct": {
        "name": "📝 Помощь промптов (Llama 3)",
        "id": "meta/meta-llama-3-8b-instruct",
        "api": "replicate",
    },
}

# -------------------------------------------------------------
# === СТОИМОСТИ ===============================================
# -------------------------------------------------------------
REPLICATE_COSTS: Dict[str, float] = {
    MULTI_LORA_MODEL: 0.000725 * 30,
    TRAINING_MODEL: 0.001525,
    "meta/meta-llama-3-8b-instruct": 0.0005,
    "kwaivgi/kling-v2.1": 0.0028 * 5,
}

# -------------------------------------------------------------
# === MAPPING TYPE -> MODEL KEY ===============================
# -------------------------------------------------------------
GENERATION_TYPE_TO_MODEL_KEY: Dict[str, Any] = {
    "with_avatar": MULTI_LORA_MODEL,
    "photo_to_photo": MULTI_LORA_MODEL,
    "ai_video_v2_1": "kwaivgi/kling-v2.1",
    "train_flux": TRAINING_MODEL,
    "prompt_assist": "meta-llama-3-8b-instruct",
    "prompt_based": {
        "real": MULTI_LORA_MODEL,
        "crea": CREATIVE_LORA_MODEL,
    },
}

# -------------------------------------------------------------
# === СТИЛЕВЫЕ КЛЮЧИ ==========================================
# -------------------------------------------------------------
from style import NEW_MALE_AVATAR_STYLES, NEW_FEMALE_AVATAR_STYLES

REALISM_STYLE_KEYS = {
    *NEW_MALE_AVATAR_STYLES.keys(),
    *NEW_FEMALE_AVATAR_STYLES.keys(),
} - {"zarz", "zarza", "style_chic", "profession"}

CREATIVE_STYLE_KEYS = {"zarz", "zarza", "profession", "style_chic"}

def is_creative_style(style_key: str) -> bool:
    return style_key in CREATIVE_STYLE_KEYS

# -------------------------------------------------------------
# === СТИЛИ ВИДЕО =============================================
# -------------------------------------------------------------
VIDEO_GENERATION_STYLES = {
    "dynamic_action": "🏃‍♂️ Динамичное действие",
    "slow_motion": "🐢 Замедленное движение",
    "cinematic_pan": "🎥 Кинематографический панорамный вид",
    "facial_expression": "😊 Выразительная мимика",
    "object_movement": "⏳ Движение объекта",
    "dance_sequence": "💃 Танцевальная последовательность",
    "nature_flow": "🌊 Естественное течение",
    "urban_vibe": "🏙 Городская атмосфера",
    "fantasy_motion": "✨ Фантастическое движение",
    "retro_wave": "📼 Ретро-волна"
}

VIDEO_STYLE_PROMPTS = {
    "dynamic_action": "A person performing dynamic action, energetic movement, athletic pose, action sequence, dynamic motion, vibrant energy, active movement, powerful gesture, dynamic pose, energetic action",
    "slow_motion": "A person in slow motion, graceful movement, elegant motion, smooth transition, gentle movement, flowing motion, serene movement, peaceful motion, calm action, slow graceful pose",
    "cinematic_pan": "Cinematic panning shot, professional camera movement, smooth camera transition, film-like motion, cinematic quality, professional videography, smooth pan, camera movement, cinematic shot, professional video",
    "facial_expression": "A person with expressive facial features, emotional expression, animated face, lively expression, dynamic facial movement, expressive eyes, animated features, emotional face, lively eyes, expressive pose",
    "object_movement": "A person interacting with objects, hand movement, object manipulation, hand gesture, object interaction, manual action, hand motion, object handling, manual movement, hand action",
    "dance_sequence": "A person dancing, dance movement, rhythmic motion, dance pose, choreographed movement, dance sequence, rhythmic action, dance gesture, choreographed pose, dance motion",
    "nature_flow": "A person in natural environment, flowing movement, natural motion, organic movement, natural pose, flowing action, natural gesture, organic motion, natural flow, environmental movement",
    "urban_vibe": "A person in urban setting, city environment, urban atmosphere, street scene, city background, urban pose, street environment, city motion, urban action, street atmosphere",
    "fantasy_motion": "A person in fantasy setting, magical movement, fantasy environment, mystical motion, magical pose, fantasy action, mystical movement, magical gesture, fantasy motion, enchanted movement",
    "retro_wave": "A person in retro style, vintage atmosphere, retro aesthetic, nostalgic motion, vintage pose, retro action, nostalgic movement, vintage gesture, retro motion, nostalgic action"
}

# -------------------------------------------------------------
# === УТИЛИТЫ =================================================
# -------------------------------------------------------------
def get_real_lora_model(name: str) -> str:
    cfg = LORA_CONFIG.get(name, {})
    return cfg.get("model", "")

def _has(tags, text: str) -> bool:
    return any(t in text for t in tags)

def _has_hair_terms(text: str) -> bool:
    return _has(["hair", "волос", "long hair", "short hair"], text)

def _has_animal_terms(text: str) -> bool:
    return _has(ANIMAL_KEYWORDS, text)

def _has_body_terms(text: str) -> bool:
    return _has(BODY_KEYWORDS, text)

def _has_piercing_terms(text: str) -> bool:
    return _has(PIERCING_KEYWORDS, text) or "portrait" in text

def _has_beach_terms(text: str) -> bool:
    return _has(BEACH_KEYWORDS, text)

def _has_neon_terms(text: str) -> bool:
    return _has(NEON_KEYWORDS + ["lamp", "lamplight", "тёплая лампа", "лампа"], text)

def _has_leaf_terms(text: str) -> bool:
    return _has(LEAF_KEYWORDS, text)

def _has_smile_terms(text: str) -> bool:
    return _has(SMILE_KEYWORDS, text)

def _has_glasses_terms(text: str) -> bool:
    return _has(GLASSES_KEYWORDS, text) or "sunglasses" in text or "очки" in text

def _has_jewelry_terms(text: str) -> bool:
    return _has(["jewelry", "украшения", "watch", "часы", "ring", "кольцо",
                 "necklace", "ожерелье", "earrings", "серьги", "bracelet", "браслет",
                 "crown", "корона", "tiara", "tiara"], text)

def stable_choice(items, key: str):
    h = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)
    return items[h % len(items)]

GLASSES_STYLES = {
    "classic_rect": "classic rectangular sunglasses, medium frame width, thin temple arms",
    "soft_round": "soft round sunglasses, medium-small frame, subtle keyhole bridge",
    "cat_eye": "gentle cat-eye sunglasses, slim arms, narrow bridge",
}

def select_glasses_style(prompt: str) -> str:
    return stable_choice(list(GLASSES_STYLES.values()), prompt.lower())

# -------------------------------------------------------------
# === СБОРКА NEGATIVE =========================================
# -------------------------------------------------------------
def build_negative_prompt(prompt: str, gen_type: str, style_key: str = "") -> tuple[str, str]:
    p = prompt.lower()
    block = (
        NEGATIVE_PROMPTS["creative_max"]
        if is_creative_style(style_key)
        else NEGATIVE_PROMPTS["ultra_realistic_max"]
        if gen_type in ("ultra", "max", "with_avatar", "photo_to_photo")
        else NEGATIVE_PROMPTS["default"]
    )

    positive_additions = []
    if _has_jewelry_terms(p):
        positive_additions.append(JEWELRY_POSITIVE_TOKENS)
        if _has(["watch", "часы", "wristwatch"], p):
            positive_additions.append(WATCH_POSITIVE_TOKENS)
        if _has(["ring", "кольцо", "wedding ring"], p):
            positive_additions.append(RING_POSITIVE_TOKENS)
        if _has(["necklace", "ожерелье", "chain", "цепочка"], p):
            positive_additions.append(NECKLACE_POSITIVE_TOKENS)
        if _has(["earrings", "серьги", "earring"], p):
            positive_additions.append(EARRINGS_POSITIVE_TOKENS)
        if _has(["bracelet", "браслет", "armband"], p):
            positive_additions.append(BRACELET_POSITIVE_TOKENS)
        if _has(["crown", "корона", "tiara"], p):
            positive_additions.append(CROWN_TIARA_POSITIVE_TOKENS)
    if _has_body_terms(p):
        positive_additions.append(CLAVICLE_POSITIVE_TOKENS)
    if _has_animal_terms(p):
        positive_additions.append(ANIMAL_POSITIVE_TOKENS)
    if _has(["object", "item", "thing", "предмет", "вещь"], p):
        positive_additions.append(OBJECT_POSITIVE_TOKENS)
    if _has_body_terms(p):
        positive_additions.append(BODY_POSITIVE_TOKENS)
    if _has_leaf_terms(p) or _has_beach_terms(p):
        positive_additions.append(DOF_POSITIVE_TOKENS)
    if _has(["flag", "флаг", "banner", "знамя"], p):
        positive_additions.append(FLAG_POSITIVE_TOKENS)
    positive_additions.append(PHOTOREALISTIC_POSITIVE_TOKENS)

    extras = [
        HAND_NEGATIVE_TOKENS if _has(HAND_KEYWORDS, p) else "",
        HAIR_NEGATIVE_TOKENS if (_has_hair_terms(p) or "portrait" in p) else "",
        SKIN_NEGATIVE_TOKENS,
        FOREHEAD_NEGATIVE_TOKENS,
        FACE_DIRT_NEGATIVE,
        EXPRESSION_NEGATIVE_TOKENS,
        SKINTONE_NEGATIVE,
        SPOTS_NEGATIVE_TOKENS if ("portrait" in p or gen_type in ("with_avatar", "photo_to_photo")) else "",
        YOUTH_NEGATIVE_TOKENS if ("portrait" in p or gen_type in ("with_avatar", "photo_to_photo")) else "",
        BEAUTY_SKIN_NEGATIVE if gen_type in ("with_avatar", "photo_to_photo", "portrait") else "",
        GLASSES_NEGATIVE_TOKENS if _has_glasses_terms(p) else "",
        COLOR_CAST_NEGATIVE, REDNESS_NEGATIVE,
        "neon magenta cast on skin, neon blue cast on skin" if _has_neon_terms(p) else "",
        "harsh midday contrast, sweaty shine" if _has_beach_terms(p) else "",
        (TREE_POSE_NEGATIVE + ", " + FACE_OCCLUSION_NEGATIVE) if _has_leaf_terms(p) else "",
        HAND_SCALE_NEGATIVE if ("portrait" in p or gen_type in ("with_avatar", "photo_to_photo")) else "",
        MAKEUP_NEGATIVE_TOKENS if ("portrait" in p or gen_type in ("with_avatar", "photo_to_photo")) else "",
        PIERCING_NEGATIVE_TOKENS if _has_piercing_terms(p) else "",
        TEETH_NEGATIVE_TOKENS if _has_smile_terms(p) else "",
        POSE_NEGATIVE_TOKENS,
        EYES_NEGATIVE_TOKENS,
        JEWELRY_NEGATIVE_TOKENS,
        WATCH_NEGATIVE_TOKENS if _has(["watch", "часы", "wristwatch"], p) else "",
        RING_NEGATIVE_TOKENS if _has(["ring", "кольцо", "wedding ring"], p) else "",
        NECKLACE_NEGATIVE_TOKENS if _has(["necklace", "ожерелье", "chain", "цепочка"], p) else "",
        EARRINGS_NEGATIVE_TOKENS if _has(["earrings", "серьги", "earring"], p) else "",
        BRACELET_NEGATIVE_TOKENS if _has(["bracelet", "браслет", "armband"], p) else "",
        CROWN_TIARA_NEGATIVE_TOKENS if _has(["crown", "корона", "tiara", "tiara"], p) else "",
        CLAVICLE_NEGATIVE_TOKENS if _has_body_terms(p) else "",
        FORBIDDEN_ELEMENTS_NEGATIVE,
        ANIMAL_NEGATIVE_TOKENS if _has_animal_terms(p) else "",
        OBJECT_NEGATIVE_TOKENS if _has(["object", "item", "thing", "предмет", "вещь"], p) else "",
        FLAG_NEGATIVE_TOKENS if _has(["flag", "флаг", "banner", "знамя"], p) else "",
        BODY_NEGATIVE_TOKENS if _has_body_terms(p) else "",
        FABRIC_NEGATIVE_TOKENS,
        BOKEH_NEGATIVE_TOKENS,
        OCCLUSION_EDGE_NEGATIVE,
        BODY_HAIR_NEGATIVE,
        NSFW_NEGATIVE,
        "Pixar skin, toon skin, anime skin, plastic toy look",
        IDENTITY_NEGATIVE_TOKENS if gen_type in ("with_avatar", "photo_to_photo", "portrait") else "",
        IDENTITY_STRONG_NEGATIVE if gen_type in ("with_avatar", "photo_to_photo", "portrait") else "",
    ]

    updated_prompt = prompt
    if positive_additions:
        updated_prompt += ", " + ", ".join(positive_additions)

    negative_prompt = ", ".join(t for t in [block, *extras] if t)

    return updated_prompt, negative_prompt

# -------------------------------------------------------------
# === КАЧЕСТВО / СИД ==========================================
# -------------------------------------------------------------
def choose_quality_params(gen_type: str, aspect: str, style_key: str = "") -> Dict[str, Any]:
    key = (
        "fast_hq" if gen_type in ["fast", "realtime"]
        else "portrait_ultra" if gen_type == "portrait_ultra"
        else "beauty_portrait" if gen_type in ("portrait", "with_avatar", "photo_to_photo")
        else "ultra_max_quality" if gen_type in ("ultra", "max")
        else "creative" if is_creative_style(style_key)
        else "default"
    )
    params = GENERATION_QUALITY_PARAMS[key].copy()
    w, h = get_resolution_by_ratio(aspect)
    params.update({"width": w, "height": h})

    params.setdefault("saturation_clamp", 0.88)
    params.setdefault("vibrance_boost", -0.04)
    params.setdefault("contrast_soft_clip", 0.92)

    params.update({
        "focus_on_faces": True,
        "focus_distance_lock": "eyes",
        "aperture": "f/1.8",
        "critical_eye_focus": True,
        "foreground_edge_protection": True,
        "depth_of_field": True,
        "lighting_mode": "natural_soft",
        "light_source": "window_light",
        "golden_hour_bias": True,
        "use_shadows": True,
        "eye_light_intensity": 0.18,
        "natural_light_bounce": True,
        "skin_detail_enhancement": True,
        "skin_texture_strength": 0.75,
        "auto_beauty": "off",
        "face_smoothing": 0.1,
        "film_grain": 0.32,
        "texture_noise_blend": 0.41,
        "skin_micro_grain": 0.38,
        "specular_breakup": 0.42,
        "skin_diffusion_bias": 0.58,
        "contact_shadow_boost": 0.34,
        "contact_shadow_size": 0.15,
        "contrast_clamp": 0.92,
        "micro_detail_boost": 0.34,
        "forehead_texture_recover": 0.23,
        "forehead_shadow_gain": 0.17,
        "eye_detail": {
            "enhance_iris": True,
            "reflections": "natural_light",
            "catchlight_intensity": 0.7,
            "pupil_shape_correction": True
        },
        "sharpness_boost": 0.12,
        "anti_cartoon_strength": 0.95,  # Усиливаем контроль "воска"
        "realism_bias": "high",
        "anti_cartoon": True,
        "individuality": {
            "subtle_asymmetry": True,
            "expression_variability": 0.4,
            "micro_features_randomness": 0.3
        },
        "saturation_boost": 0.93,
        "skin_tone_correct": 0.86,
        "texture_enhance": 0.3,
        "denoise_strength": 0.65,
        "sharpness_postproc": 0.05,
        "makeup_enhance": "natural",
        "random_seed": False,
        "seed": 42069
    })

    if gen_type in ("portrait", "with_avatar", "photo_to_photo"):
        params["guidance_scale"] = max(1.20, params["guidance_scale"] - 0.15)
        params["scheduler"] = "UniPC"
    params.setdefault("film_grain", 0.15)

    # гарантируем защиту края и микротекстуру
    params["foreground_edge_protection"] = True
    params.setdefault("micro_detail_boost", 0.45)
    params.setdefault("skin_micro_grain", 0.50)
    if params.get("denoise_strength", 0.65) > 0.55:
        params["skin_micro_grain"]  = max(0.50, params["skin_micro_grain"])
        params["texture_noise_blend"] = max(0.50, params.get("texture_noise_blend", 0.41))

    # Foreground Edge-Protection при DOF
    if params.get("depth_of_field"):
        params["foreground_edge_protection"] = True

    return params

def select_camera_shot(p_low: str, key: str = "") -> str:
    pool: list[str] = []
    for k, d in CAMERA_SHOTS.items():
        w = int(d["weight"] * (2 if _has(d["keywords"], p_low) else 1) * 100)
        if k in ["extreme_close_up", "close_up", "medium_shot"]:
            w = int(w * 1.2)
        if w > 0:
            pool.extend([k] * w)
    if not key:
        key = p_low
    return stable_choice(pool, key)

# -------------------------------------------------------------
# === AUTO‑BEAUTY 2.0: ПРАВИЛА И ДЕЙСТВИЯ =====================
# -------------------------------------------------------------
AUTO_BEAUTY_RULES: Dict[str, Any] = {
    "thresholds": {
        "ok": {
            "redness_score": 0.26,
            "blotchiness_score": 0.23,
            "neon_cast_score": 0.14,
            "cyan_cast_score": 0.14,
            "forehead_crease_saliency": 0.10,
            "shine_score": 0.12,
            "texture_noise_score": 0.16,
            "artifact_score": 0.16,
            "face_spots_count": 2,
            "beauty_score": 0.70,
            "waxy_score": 0.02,        # Усиливаем контроль "воска"
        },
        "fixable": {
            "redness_score": 0.34,
            "blotchiness_score": 0.36,
            "neon_cast_score": 0.22,
            "cyan_cast_score": 0.22,
            "forehead_crease_saliency": 0.18,
            "shine_score": 0.25,
            "texture_noise_score": 0.25,
            "artifact_score": 0.25,
            "face_spots_count": 3,
            "beauty_score": 0.38,
            "waxy_score": 0.10,
        },
    },
    "actions": {
        "tone_color": {
            "white_balance_lock": True,
            "skin_tone_protect": 0.72,
            "saturation_clamp": 0.82,
            "vibrance_boost": -0.06,
            "hue_stability": 0.86,
            "decast_neon": 0.55,
            "decast_cyan": 0.50,
        },
        "texture_soften": {
            "forehead_smoothing": 0.25,
            "skin_texture_blend": 0.10,
            "shine_control": 0.55,
        },
        "detail_preserve": {
            "micro_pores_recover": 0.90,
            "specular_breakup": 0.42,
            "anti_wax_guard": True,
        },
        "blemish_cleanup": {
            "moles_limit": 1,
            "blemish_cleanup_strength": 0.5,
            "spot_max_area_px": 12,
        },
        "sampler_tweaks": {
            "guidance_delta": -0.18,
            "steps_delta": +10,
        },
    },
    "severe_reject": True,
    "min_trigger_delta": 0.04,
    "studio_lighting_exceptions": {
        "max_contrast_ratio": 0.7
    }
}

# -------------------------------------------------------------
# === ОСНОВНОЙ ПЛАН LoRA / ТОКЕНЫ =============================
# -------------------------------------------------------------
def get_optimal_lora_config(prompt: str, gen_type: str, style_key: str = "") -> Dict[str, Any]:
    # Проверка NSFW-контента
    if is_nsfw_prompt(prompt):
        raise ValueError("❌ Запрошена откровенная/NSFW-сцена. Генерация запрещена.")

    p_low = prompt.lower()
    is_creative = is_creative_style(style_key)
    has_animals = _has_animal_terms(p_low)
    has_body = _has_body_terms(p_low)

    if is_creative:
        preset, cam = "art_style", "mixed soft & hard rim, vibrant gels"
    elif "portrait" in p_low or gen_type in ("with_avatar", "photo_to_photo"):
        preset, cam = "portrait_pro", CAMERA_SETUP_BEAUTY
    else:
        preset, cam = "photo_max", (CAMERA_SETUP_HAIR if _has_hair_terms(p_low) else CAMERA_SETUP_BASE)

    shot = select_camera_shot(p_low, prompt)
    aspect = (
        "4:5" if shot in ["close_up", "extreme_close_up", "medium_shot", "waist_shot"] else
        "16:9" if shot in ["long_shot", "low_angle", "high_angle", "dutch_angle", "over_shoulder"] else
        "3:4"
    )

    loras = ["avatar_personal_lora"] + LORA_STYLE_PRESETS[preset]["loras"][:]
    need_hands = (not has_animals) and (
        _has(HAND_KEYWORDS, p_low)
        or shot in ["medium_shot", "full_shot", "long_shot", "low_angle", "high_angle"]
    )
    if need_hands and "hands_ultra" not in loras:
        if ("avatar_personal_lora" not in loras) or (len(loras) < MAX_LORA_COUNT):
            loras.append("hands_ultra")
        else:
            repl = "skin_detail_soft" if "skin_detail_soft" in loras else loras[-1]
            loras[loras.index(repl)] = "hands_ultra"

    if has_body and "body_realism" not in loras:
        if ("avatar_personal_lora" not in loras) or (len(loras) < MAX_LORA_COUNT):
            loras.append("body_realism")
        else:
            worst = sorted(loras, key=lambda x: LORA_PRIORITIES.get(x, 99))[-1]
            loras[loras.index(worst)] = "body_realism"

    glasses_style = select_glasses_style(prompt) if _has_glasses_terms(p_low) else ""

    lora_config = {
        "pose": "neutral",
        "style": "photoreal",
        "identity_lock": True,
        "priority": ["face", "hands"],
        "realism_bias": "high",
        "anti_cartoon_strength": 0.95,  # Усиливаем контроль "воска"
    }

    positives = ", ".join(
        t
        for t in [
            "photographic realism, DSLR optics, neutral white balance, natural lighting",
            "85mm lens, f/1.8 aperture, shallow depth of field, natural bokeh",
            "golden hour lighting, soft window light, natural shadows",
            HAIR_POSITIVE_TOKENS if (_has_hair_terms(p_low) or "portrait" in p_low) else "",
            SKIN_POSITIVE_TOKENS,
            SKIN_MICRO_GRAIN,
            SKINTONE_POSITIVE,
            SPOTS_POSITIVE_TOKENS if ("portrait" in p_low or gen_type in ("with_avatar", "photo_to_photo")) else "",
            BEAUTY_SKIN_POSITIVE if ("portrait" in p_low or gen_type in ("with_avatar", "photo_to_photo")) else "",
            YOUTH_POSITIVE_TOKENS if ("portrait" in p_low or gen_type in ("with_avatar", "photo_to_photo")) else "",
            MAKEUP_POSITIVE_TOKENS if ("portrait" in p_low or gen_type in ("with_avatar", "photo_to_photo")) else "",
            FOREHEAD_SMOOTH_POSITIVE,
            GLASSES_POSITIVE_TOKENS if _has_glasses_terms(p_low) else "",
            glasses_style,
            EXPRESSION_POSITIVE_TOKENS,
            FACE_CLEAR_POSITIVE if _has_leaf_terms(p_low) else "",
            SAFE_HAND_POSE_POSITIVE if (_has_leaf_terms(p_low) or need_hands) else "",
            CONTACT_PHYSICS_POSITIVE,
            "asymmetric eye catchlights, natural tear line highlight",
            "accurate contact shadows under nose and lips, strap indentation with soft shadow, occlusion between fingers and object, "
            "soft contact shadows under lips and nose, natural lip shadows, micro specular breakup on lips, "
            "asymmetric lip details, soft lip corners, uneven upper lip thickness, "
            "natural cheek shadows, asymmetric lip detail, soft contact shadows, ambient bounce from wall, "
            "subtle forehead texture, realistic skin specular breakup, matte skin finish, visible pore detail, diffuse bounce light, "
            "soft sunlight from window, daylight shadows on skin, realistic cheek shadow, natural nasolabial crease, "
            "matte skin texture, realistic skin specular breakup, asymmetric face shape, realistic jawline, "
            "subtle cheek shadows, asymmetric lip detail, soft ambient bounce light, ambient rim light, "
            "realistic forehead specular breakup, natural skin microdetail, warm edge light, nasolabial shadow, "
            "skin pores, peach fuzz, fine facial detail, soft side lighting, natural oil on skin, "
            "real skin pores, subtle color noise, ambient bounce from wall, asymmetric lip detail, "
            "soft contact shadows, natural cheek shadows, realistic specular breakup, gentle glow transitions, "
            "face planes subtly emphasized, natural cheek shadows, nasolabial shadow, subtle forehead texture, "
            "slight pores, realistic skin variation, soft light diffusion on nose, slight under-eye shadow",
            "natural cheek shadows, soft contact shadows, ambient bounce from wall, subtle forehead texture, "
            "realistic skin specular breakup, slight pores, realistic skin variation, soft light diffusion on nose, slight under-eye shadow",
            "ambient bounce from daylight, pores visibility, realistic skin texture, asymmetric lip detail, "
            "ambient bounce from wall, soft contact shadows, cheek roll-off, "
            "natural cheek shadows, soft contact shadows, ambient bounce from wall, "
            "subtle forehead texture, realistic skin specular breakup, slight pores, "
            "realistic skin variation, soft light diffusion on nose, slight under-eye shadow",
            TEETH_POSITIVE_TOKENS if _has_smile_terms(p_low) else "",
            PIERCING_POSITIVE_TOKENS if _has_piercing_terms(p_low) else "",
            HAND_POSITIVE_TOKENS if need_hands else "",
            BODY_POSITIVE_TOKENS if has_body else "",
            ANIMAL_CONTACT_POSITIVE if has_animals else "",
            EYES_POSITIVE_TOKENS,
            POSE_POSITIVE_TOKENS,
            POSE_SAFETY_POSITIVE,
            ENVIRONMENT_POSITIVE,
            IDENTITY_POSITIVE_TOKENS + ", photo matches reference face" if ("portrait" in p_low or gen_type in ("with_avatar", "photo_to_photo")) else "",
            IDENTITY_STRONG_POSITIVE if ("portrait" in p_low or gen_type in ("with_avatar", "photo_to_photo")) else "",
            DOF_POSITIVE_TOKENS,
            PRO_COMPOSITION_POSITIVE,
        ]
        if t
    )

    q = choose_quality_params(gen_type, aspect, style_key)

    if _has_neon_terms(p_low):
        q.update({
            "white_balance_lock": True,
            "skin_tone_protect": 0.62,
            "saturation_clamp": 0.84,
            "decast_neon": 0.55,
            "decast_cyan": 0.50
        })
        q["num_inference_steps"] = min(q.get("num_inference_steps", 140) + 10, 180)
    if _has_beach_terms(p_low) or _has_leaf_terms(p_low):
        q.update({
            "white_balance_lock": True,
            "skin_tone_protect": 0.62,
            "saturation_clamp": 0.84,
            "contact_shadow_size": 0.22,
            "contact_shadow_boost": 0.45
        })
        q["num_inference_steps"] = min(q.get("num_inference_steps", 140) + 20, 180)

        # Дополнительная защита для пляжных кадров
        if _has_beach_terms(p_low):
            NEG_LITE = "t-back, g-string, microkini, topless, sideboob"
            negative_prompt += ", " + NEG_LITE

    if need_hands:
        q["num_inference_steps"] = min(q.get("num_inference_steps", 140) + 20, 200)
        q["guidance_scale"] = max(1.30, q.get("guidance_scale", 1.44))
    if _has_glasses_terms(p_low):
        q["num_inference_steps"] = min(q.get("num_inference_steps", 140) + 5, 180)

    q.setdefault("seed_lock", True)
    q.setdefault("seed_jitter", 3)
    q["face_anchor"] = True
    q.setdefault("texture_noise_blend", 0.41)
    q.setdefault("environment_detail_enhance", True)
    q.setdefault("contact_shadow_boost", 0.34)
    q.setdefault("hand_size_regularizer", True)
    q.setdefault("glasses_size_jitter_limit", GLASSES_RULES["size_jitter_limit"])
    q.setdefault("bokeh_water_de-tiling", True)
    q.setdefault("film_grain", 0.32)
    q.setdefault("skin_micro_grain", 0.38)
    q.setdefault("specular_breakup", 0.42)
    q.setdefault("contact_shadow_size", 0.15)
    q.setdefault("contrast_clamp", 0.92)
    q.setdefault("micro_detail_boost", 0.34)
    q.setdefault("forehead_texture_recover", 0.23)
    q.setdefault("forehead_shadow_gain", 0.17)
    q.setdefault("skin_diffusion_bias", 0.58)

    q.update({
        "auto_beauty_enabled": True,
        "auto_beauty_rules": AUTO_BEAUTY_RULES,
    })

    updated_prompt, negative_prompt = build_negative_prompt(prompt, gen_type, style_key)

    return {
        "loras": loras,
        "quality_params": q,
        "negative_prompt": negative_prompt,
        "camera_setup": CAMERA_SETUP_BEAUTY if ("portrait" in p_low or gen_type in ("with_avatar", "photo_to_photo")) else CAMERA_SETUP_BASE,
        "shot_plan": CAMERA_SHOTS[shot]["description"],
        "aspect_ratio": aspect,
        "positive_tokens": updated_prompt,
        "glasses_style": glasses_style,
    }

# -------------------------------------------------------------
# === ПРЕСЕТЫ СТИЛЕЙ ==========================================
# -------------------------------------------------------------
LORA_STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "photo_max": {"loras": ["base_realism", "hands_five_fix", "hands_precision", "face_ultra", "skin_detail"], "quality_params": "ultra_max_quality"},
    "portrait_pro": {"loras": ["base_realism", "hands_five_fix", "hands_precision", "face_ultra", "skin_detail"], "quality_params": "beauty_portrait"},
    "art_style": {"loras": ["art_explorer"], "quality_params": "creative"},
}

# -------------------------------------------------------------
# === ПАРАМЕТРЫ КАЧЕСТВА ======================================
# -------------------------------------------------------------
GENERATION_QUALITY_PARAMS: Dict[str, Dict[str, Any]] = {
    "fast_hq": {
        "guidance_scale": 2.6,
        "num_inference_steps": 60,
        "scheduler": "UniPC",
        "controlnet": [
            {"id": "lllyasviel/control_v11p_sd15_openpose", "type": "openpose_hand", "weight": 1.25},
            {"id": "TencentARC/t2iadapter_hand-diffusion-xl", "type": "t2i_hand_adapter", "weight": 0.90}
        ],
        "hand_pose_guidance": True,
        "hand_size_regularizer": True
    },
    "default": {
        "guidance_scale": 2.8,
        "num_inference_steps": 80,
        "scheduler": "UniPC",
        "controlnet": [
            {"id": "lllyasviel/control_v11p_sd15_openpose", "type": "openpose_hand", "weight": 1.25},
            {"id": "TencentARC/t2iadapter_hand-diffusion-xl", "type": "t2i_hand_adapter", "weight": 0.90}
        ],
        "hand_pose_guidance": True,
        "hand_size_regularizer": True
    },
    "ultra_max_quality": {
        "guidance_scale": 3.12,
        "num_inference_steps": 200,
        "scheduler": "DPM++2M Karras",
        "controlnet": [
            {"id": "lllyasviel/control_v11p_sd15_openpose", "type": "openpose_hand", "weight": 1.25},
            {"id": "TencentARC/t2iadapter_hand-diffusion-xl", "type": "t2i_hand_adapter", "weight": 0.90}
        ],
        "hand_pose_guidance": True,
        "hand_size_regularizer": True,
        "micro_detail_boost": 0.55,   # Усиливаем микротекстуру
        "skin_micro_grain": 0.55,     # Усиливаем зернистость кожи
        "specular_breakup": 0.60,     # Разнесённые блики
        "contact_shadow_boost": 0.45
    },
    "portrait_ultra": {
        "guidance_scale": 1.88,
        "num_inference_steps": 135,
        "scheduler": "DDIM",
        "controlnet": [
            {"id": "lllyasviel/control_v11p_sd15_openpose", "type": "openpose_hand", "weight": 1.25},
            {"id": "TencentARC/t2iadapter_hand-diffusion-xl", "type": "t2i_hand_adapter", "weight": 0.90}
        ],
        "hand_pose_guidance": True,
        "hand_size_regularizer": True
    },
    "beauty_portrait": {
        "guidance_scale": 2.5,
        "num_inference_steps": 140,
        "scheduler": "DDIM",
        "controlnet": [
            {"id": "lllyasviel/control_v11p_sd15_openpose", "type": "openpose_hand", "weight": 1.25},
            {"id": "TencentARC/t2iadapter_hand-diffusion-xl", "type": "t2i_hand_adapter", "weight": 0.90}
        ],
        "hand_pose_guidance": True,
        "hand_size_regularizer": True,
        "micro_detail_boost": 0.55,   # Усиливаем микротекстуру
        "skin_micro_grain": 0.55,     # Усиливаем зернистость кожи
        "specular_breakup": 0.60,     # Разнесённые блики
        "contact_shadow_boost": 0.45
    },
    "creative": {
        "guidance_scale": 2.8,
        "num_inference_steps": 50,
        "scheduler": "UniPC",
        "controlnet": [
            {"id": "lllyasviel/control_v11p_sd15_openpose", "type": "openpose_hand", "weight": 1.25},
            {"id": "TencentARC/t2iadapter_hand-diffusion-xl", "type": "t2i_hand_adapter", "weight": 0.90}
        ],
        "hand_pose_guidance": True,
        "hand_size_regularizer": True
    },
}

# -------------------------------------------------------------
# === ПОСТ‑ФИЛЬТР / ОТБРАКОВКА ================================
# -------------------------------------------------------------
POSE_REJECTION_RULES: Dict[str, Any] = {
    "max_head_turn_deg": 32,
    "max_head_tilt_deg": 12,
    "forbid_back_view": True,
    "max_wrist_bend_deg": 35,
    "max_wrist_deviation_deg": 20,
    "max_elbow_hyperext_deg": 7,
    "min_thumb_opposition": 0.5,
    "require_thumb_visible_in_grip": True,
    "forbid_two_hands_full_wrap_cylinder": True,
    "forbid_arm_behind_head_near_object": True,
    "require_contact_shadows": True,
    "require_strap_indentation": True,
    "hand_face_scale_ratio_range": (0.65, 1.50),
    "max_hand_count": 3,
    "max_arm_count": 2,
    "require_finger_count": 5,
    "forbid_missing_finger": True,
    "forbid_extra_finger": True,
    "max_neck_flex_deg": 20,
    "min_neck_length_ratio": 0.25,
    "max_neck_length_ratio": 0.45,
    "max_finger_merge_ratio": 0.02,
    "max_missing_finger": 0,
    "min_detected_finger_count": 5,
    "finger_order_check": True,          # thumb–index–middle–ring–pinky, left→right
    "reject_misordered_index_ring": True,
    "forbid_palm_through_object": True,
    "require_nail_visible": False,
    "reject_if_finger_count_mismatch": True,   # Жёстко запрещаем < 5 / > 5 пальцев
    "auto_fix_minor_finger_shift": False,      # Отключаем авто-исправление
    "glasses_rules": GLASSES_RULES,
    "min_face_clear_margin": 0.03,
    "face_skin_rules": {
        "max_forehead_crease_saliency": 0.14,
        "max_redness_score": 0.22,
        "max_face_spots_count": 2,
        "max_single_spot_area_px": 24,
        "max_shine_score": 0.22,
        "max_waxy_score": 0.10,
        "max_cartoon_score": 0.08,
        "auto_fix_if_minor": True,
        "use_auto_beauty_rules": True,
        "reject_if_exceeds": True
    },
    "forbid_pronation_supination_conflict": True,
    "reject_messages": {
        "head": "⚠ Слишком большой поворот/наклон головы — возможны искажения лица.",
        "wrist": "⚠ Нереалистичный изгиб/девиация запястья — заменить позу.",
        "elbow": "⚠ Гиперэкстензия локтя — заменить позу.",
        "thumb": "⚠ Большой палец не в оппозиции/не виден — хват выглядит неестественно.",
        "wrap": "⚠ Полный охват вертикального ствола двумя руками — запрет (смотрится неестественно).",
        "shadow": "⚠ Нет контактной тени/индента — ощущение «наклейки».",
        "scale": "⚠ Масштаб кисти относительно лица некорректный.",
        "fingers": "⚠ Некорректное количество пальцев / деформация – отклоняем.",
        "neck": "⚠ Неестественная длина/изгиб шеи – отклоняем.",
        "glasses": "⚠ Ошибка очков: нет двух дужек/неверный мост/нет рефракции/большой джиттер размера.",
        "axis": "⚠ Конфликт осей предплечья (пронация/супинация) с положением локтя.",
        "face": "⚠ Объект слишком близко к лицу/перекрывает контур — отклоняем.",
        "skin": "⚠ Лицо: избыточные складки лба/краснота/каст/пятна/блеск — кадр отклонён или авто‑коррекция.",
    }
}

# -------------------------------------------------------------
# === API: УТИЛИТЫ ============================================
# -------------------------------------------------------------
def get_max_quality_params() -> Dict[str, Any]:
    return GENERATION_QUALITY_PARAMS["ultra_max_quality"]

def get_ultra_negative_prompt() -> str:
    return NEGATIVE_PROMPTS["ultra_realistic_max"]

def start_avatar_training(image_dir: str, model_name: str = TRAINING_CONFIG["output_name"]) -> str:
    from replicate import Client
    client = Client()
    run = client.run(
        TRAINING_MODEL,
        input={
            "images": image_dir,
            "resolution": TRAINING_CONFIG["resolution"],
            "train_batch_size": TRAINING_CONFIG["train_batch_size"],
            "learning_rate": TRAINING_CONFIG["learning_rate"],
            "lr_scheduler": TRAINING_CONFIG["lr_scheduler"],
            "max_train_steps": TRAINING_CONFIG["max_train_steps"],
            "save_every_n_steps": TRAINING_CONFIG["save_every_n_steps"],
            "mixed_precision": TRAINING_CONFIG["mixed_precision"],
            "lora_name": model_name,
            "enable_identity_loss": TRAINING_CONFIG.get("enable_identity_loss", False),
            "identity_loss_weight": TRAINING_CONFIG.get("identity_loss_weight", 0.0),
        }
    )
    return run.model.id

def get_person_model() -> str:
    return TRAINING_CONFIG["output_name"]

def is_nsfw_prompt(text: str) -> bool:
    """Проверяет, содержит ли промпт NSFW-контент"""
    ban = [
        "nude", "erotic", "nsfw", "裸", "裸体",
        "topless", "naked", "exposed genitals", "spread legs",
        "cum", "sexual", "penetration", "sex"
    ]
    return any(w in text.lower() for w in ban)

def apply_auto_beauty(metrics: Dict[str, float], params: Dict[str, Any]) -> Dict[str, Any]:
    rules = AUTO_BEAUTY_RULES
    t_ok, t_fx = rules["thresholds"]["ok"], rules["thresholds"]["fixable"]

    def over(m, k, lim): return m.get(k, 0.0) > lim

    minor = (
        (over(metrics, "redness_score", t_ok["redness_score"]) or
         over(metrics, "blotchiness_score", t_ok["blotchiness_score"]) or
         over(metrics, "neon_cast_score", t_ok["neon_cast_score"]) or
         over(metrics, "cyan_cast_score", t_ok["cyan_cast_score"]) or
         over(metrics, "forehead_crease_saliency", t_ok["forehead_crease_saliency"]) or
         over(metrics, "shine_score", t_ok["shine_score"]) or
         over(metrics, "texture_noise_score", t_ok["texture_noise_score"]) or
         over(metrics, "artifact_score", t_ok["artifact_score"]) or
         metrics.get("face_spots_count", 0) > t_ok["face_spots_count"] or
         metrics.get("beauty_score", 1.0) < t_ok["beauty_score"])
        and not (
         over(metrics, "redness_score", t_fx["redness_score"]) or
         over(metrics, "blotchiness_score", t_fx["blotchiness_score"]) or
         over(metrics, "neon_cast_score", t_fx["neon_cast_score"]) or
         over(metrics, "cyan_cast_score", t_fx["cyan_cast_score"]) or
         over(metrics, "forehead_crease_saliency", t_fx["forehead_crease_saliency"]) or
         over(metrics, "shine_score", t_fx["shine_score"]) or
         over(metrics, "texture_noise_score", t_fx["texture_noise_score"]) or
         over(metrics, "artifact_score", t_fx["artifact_score"]) or
         metrics.get("face_spots_count", 0) > t_fx["face_spots_count"] or
         metrics.get("beauty_score", 1.0) < t_fx["beauty_score"])
    )

    if minor:
        p = params.copy()
        p.update(rules["actions"]["tone_color"])
        p.update(rules["actions"]["texture_soften"])
        p.update(rules["actions"]["detail_preserve"])
        p.update(rules["actions"]["blemish_cleanup"])
        p["guidance_scale"] = max(1.08, p.get("guidance_scale", 1.44) + rules["actions"]["sampler_tweaks"]["guidance_delta"])
        p["num_inference_steps"] = min(p.get("num_inference_steps", 140) + rules["actions"]["sampler_tweaks"]["steps_delta"], 180)
        p["auto_beauty_applied"] = True
        return p

    return params

# -------------------------------------------------------------
# === ЭКСПОРТ ================================================
# -------------------------------------------------------------
__all__ = [
    "MULTI_LORA_MODEL", "HF_LORA_MODELS", "IMAGE_GENERATION_MODELS",
    "TRAINING_MODEL", "TRAINING_CONFIG", "REPLICATE_COSTS",
    "LORA_CONFIG", "LORA_PRIORITIES", "LORA_STYLE_PRESETS",
    "USER_AVATAR_LORA_STRENGTH", "MAX_LORA_COUNT",
    "HAIR_POSITIVE_TOKENS", "HAIR_NEGATIVE_TOKENS",
    "SKIN_POSITIVE_TOKENS", "SKIN_NEGATIVE_TOKENS",
    "SKINTONE_POSITIVE", "SKINTONE_NEGATIVE",
    "SPOTS_POSITIVE_TOKENS", "SPOTS_NEGATIVE_TOKENS",
    "SKIN_MICRO_GRAIN",
    "BEAUTY_SKIN_POSITIVE", "BEAUTY_SKIN_NEGATIVE",
    "FOREHEAD_SMOOTH_POSITIVE", "FOREHEAD_NEGATIVE_TOKENS",
    "COLOR_CAST_NEGATIVE", "REDNESS_NEGATIVE",
    "YOUTH_POSITIVE_TOKENS", "YOUTH_NEGATIVE_TOKENS",
    "MAKEUP_POSITIVE_TOKENS", "MAKEUP_NEGATIVE_TOKENS",
    "GLASSES_KEYWORDS", "GLASSES_POSITIVE_TOKENS", "GLASSES_NEGATIVE_TOKENS", "GLASSES_STYLES", "GLASSES_RULES",
    "PIERCING_POSITIVE_TOKENS", "PIERCING_NEGATIVE_TOKENS", "PIERCING_KEYWORDS",
    "EYES_POSITIVE_TOKENS", "EYES_NEGATIVE_TOKENS",
    "JEWELRY_POSITIVE_TOKENS", "JEWELRY_NEGATIVE_TOKENS",
    "FABRIC_POSITIVE_TOKENS", "FABRIC_NEGATIVE_TOKENS",
    "DOF_POSITIVE_TOKENS", "BOKEH_NEGATIVE_TOKENS",
    "PRO_COMPOSITION_POSITIVE",
    "HAND_KEYWORDS", "HAND_POSITIVE_TOKENS", "HAND_NEGATIVE_TOKENS",
    "POSE_POSITIVE_TOKENS", "POSE_NEGATIVE_TOKENS", "POSE_GUIDE", "POSE_SAFETY_POSITIVE",
    "IDENTITY_POSITIVE_TOKENS", "IDENTITY_NEGATIVE_TOKENS",
    "IDENTITY_STRONG_POSITIVE", "IDENTITY_STRONG_NEGATIVE",
    "ANIMAL_KEYWORDS", "ANIMAL_POSITIVE_TOKENS", "ANIMAL_NEGATIVE_TOKENS", "ANIMAL_CONTACT_POSITIVE",
    "BODY_KEYWORDS", "BODY_POSITIVE_TOKENS", "BODY_NEGATIVE_TOKENS",
    "BEACH_KEYWORDS", "NEON_KEYWORDS", "LEAF_KEYWORDS",
    "NEGATIVE_PROMPTS", "CAMERA_SHOTS",
    "CAMERA_SETUP_BASE", "CAMERA_SETUP_HAIR", "CAMERA_SETUP_BEAUTY", "LUXURY_DETAILS_BASE",
    "ASPECT_RATIOS", "GENERATION_QUALITY_PARAMS", "GENERATION_TYPE_TO_MODEL_KEY",
    "get_real_lora_model", "get_optimal_lora_config",
    "get_max_quality_params", "get_ultra_negative_prompt",
    "start_avatar_training", "get_person_model",
    "select_camera_shot", "get_resolution_by_ratio",
    "select_glasses_style", "stable_choice",
    "OCCLUSION_EDGE_NEGATIVE", "POSE_REJECTION_RULES",
    "EXPRESSION_POSITIVE_TOKENS", "EXPRESSION_NEGATIVE_TOKENS",
    "TREE_POSE_NEGATIVE", "FACE_OCCLUSION_NEGATIVE", "HAND_SCALE_NEGATIVE",
    "FACE_CLEAR_POSITIVE", "SAFE_HAND_POSE_POSITIVE", "CONTACT_PHYSICS_POSITIVE",
    "AUTO_BEAUTY_RULES", "apply_auto_beauty", "is_nsfw_prompt",
    "VIDEO_GENERATION_STYLES", "VIDEO_STYLE_PROMPTS",
    "PROFESSIONAL_PROMPTS", "VIDEO_PROMPTS", "ENHANCED_PROMPTS",
    "get_enhanced_prompt", "analyze_prompt_intent", "create_optimized_prompt"
]

# Инициализация логгера
from logger import get_logger
logger = get_logger('generation')

logger.info("✅ Skin Realism v11: Уровень 'фото со смартфона' — максимальный фотореализм с естественным светом, устранение жирной восковой текстуры, восстановление естественного светотеневого рисунка, реалистичные контактные тени, восстановление пористости и деталей.")

# -------------------------------------------------------------
# === ПРОФЕССИОНАЛЬНЫЕ ПРОМПТЫ ===============================
# -------------------------------------------------------------

# Базовые промпты для разных типов генерации
PROFESSIONAL_PROMPTS = {
    "portrait": {
        "base": "professional portrait photography, 8K ultra-realistic, natural lighting, studio quality, sharp focus, detailed facial features, natural skin texture, professional camera settings",
        "variations": {
            "business": "business professional portrait, formal attire, corporate environment, confident pose, professional lighting, executive portrait style",
            "casual": "casual portrait, relaxed expression, natural pose, soft lighting, everyday clothing, authentic moment",
            "artistic": "artistic portrait, creative lighting, dramatic shadows, artistic composition, expressive face, creative photography",
            "fashion": "fashion portrait, stylish clothing, fashion photography, editorial style, professional makeup, high-end fashion",
            "beauty": "beauty portrait, flawless skin, professional makeup, beauty lighting, glamorous style, magazine quality"
        }
    },
    "environmental": {
        "base": "environmental portrait, natural setting, environmental storytelling, contextual background, lifestyle photography, authentic moment",
        "variations": {
            "urban": "urban environment, city background, street photography style, urban atmosphere, city life, metropolitan setting",
            "nature": "natural environment, outdoor setting, nature background, environmental portrait, natural lighting, organic setting",
            "indoor": "indoor setting, interior design, home environment, domestic scene, indoor lighting, comfortable setting",
            "workplace": "workplace environment, professional setting, office background, work environment, professional context",
            "social": "social setting, group environment, social interaction, community setting, social context"
        }
    },
    "action": {
        "base": "dynamic action shot, movement capture, athletic pose, energetic motion, action photography, dynamic composition",
        "variations": {
            "sports": "sports action, athletic movement, sports photography, dynamic pose, athletic performance, sports environment",
            "dance": "dance movement, graceful motion, dance photography, artistic movement, choreographed pose, dance expression",
            "fitness": "fitness action, workout pose, fitness photography, athletic movement, exercise pose, fitness environment",
            "lifestyle": "lifestyle action, everyday movement, lifestyle photography, natural motion, authentic movement, daily activity",
            "performance": "performance action, artistic movement, performance photography, expressive motion, creative movement"
        }
    },
    "conceptual": {
        "base": "conceptual photography, artistic concept, creative composition, symbolic imagery, artistic expression, creative vision",
        "variations": {
            "abstract": "abstract concept, artistic abstraction, creative interpretation, symbolic meaning, artistic expression, conceptual art",
            "surreal": "surreal concept, dreamlike imagery, fantastical elements, imaginative composition, creative fantasy, artistic vision",
            "minimalist": "minimalist concept, simple composition, clean design, minimal elements, artistic simplicity, clean aesthetic",
            "dramatic": "dramatic concept, intense emotion, powerful imagery, dramatic lighting, emotional impact, strong visual statement",
            "whimsical": "whimsical concept, playful imagery, lighthearted mood, creative fun, artistic playfulness, cheerful expression"
        }
    },
    "fashion": {
        "base": "fashion photography, stylish clothing, fashion editorial, professional styling, fashion model, high-end fashion",
        "variations": {
            "streetwear": "street fashion, casual style, urban fashion, streetwear photography, contemporary style, modern fashion",
            "elegant": "elegant fashion, sophisticated style, luxury fashion, elegant pose, refined style, high-end elegance",
            "avant-garde": "avant-garde fashion, experimental style, creative fashion, artistic clothing, innovative design, creative style",
            "vintage": "vintage fashion, retro style, classic fashion, nostalgic clothing, timeless style, classic elegance",
            "modern": "modern fashion, contemporary style, current trends, modern clothing, contemporary fashion, current style"
        }
    }
}

# Промпты для видео
VIDEO_PROMPTS = {
    "dynamic_action": "A person performing dynamic action, energetic movement, athletic pose, action sequence, dynamic motion, vibrant energy, active movement, powerful gesture, dynamic pose, energetic action, smooth camera movement, professional videography",
    "slow_motion": "A person in slow motion, graceful movement, elegant motion, smooth transition, gentle movement, flowing motion, serene movement, peaceful motion, calm action, slow graceful pose, cinematic slow motion, professional camera work",
    "cinematic_pan": "Cinematic panning shot, professional camera movement, smooth camera transition, film-like motion, cinematic quality, professional videography, smooth pan, camera movement, cinematic shot, professional video, movie-quality cinematography",
    "facial_expression": "A person with expressive facial features, emotional expression, animated face, lively expression, dynamic facial movement, expressive eyes, animated features, emotional face, lively eyes, expressive pose, close-up cinematography",
    "object_movement": "A person interacting with objects, hand movement, object manipulation, hand gesture, object interaction, manual action, hand motion, object handling, manual movement, hand action, detailed hand cinematography",
    "dance_sequence": "A person dancing, dance movement, rhythmic motion, dance pose, choreographed movement, dance sequence, rhythmic action, dance gesture, choreographed pose, dance motion, professional dance cinematography",
    "nature_flow": "A person in natural environment, flowing movement, natural motion, organic movement, natural pose, flowing action, natural gesture, organic motion, natural flow, environmental movement, nature cinematography",
    "urban_vibe": "A person in urban setting, city environment, urban atmosphere, street scene, city background, urban pose, street environment, city motion, urban action, street atmosphere, urban cinematography",
    "fantasy_motion": "A person in fantasy setting, magical movement, fantasy environment, mystical motion, magical pose, fantasy action, mystical movement, magical gesture, fantasy motion, enchanted movement, fantasy cinematography",
    "retro_wave": "A person in retro style, vintage atmosphere, retro aesthetic, nostalgic motion, vintage pose, retro action, nostalgic movement, vintage gesture, retro motion, nostalgic action, retro cinematography"
}

# Улучшенные промпты для разных сценариев
ENHANCED_PROMPTS = {
    "professional": {
        "business": "professional business portrait, executive style, formal attire, corporate environment, confident pose, professional lighting, high-quality photography, sharp focus, natural skin texture, professional camera settings, executive portrait style, business environment",
        "casual": "casual lifestyle portrait, relaxed expression, natural pose, soft lighting, everyday clothing, authentic moment, natural environment, comfortable setting, genuine expression, lifestyle photography, natural skin texture, authentic mood",
        "creative": "creative artistic portrait, artistic lighting, creative composition, artistic expression, creative photography, artistic vision, creative pose, artistic mood, creative environment, artistic style, creative camera work, artistic quality"
    },
    "environmental": {
        "urban": "urban environmental portrait, city background, street photography style, urban atmosphere, city life, metropolitan setting, urban environment, street scene, city context, urban lifestyle, street photography, urban mood",
        "nature": "natural environmental portrait, outdoor setting, nature background, environmental storytelling, natural lighting, organic setting, natural environment, outdoor scene, nature context, environmental photography, natural mood",
        "indoor": "indoor environmental portrait, interior setting, home environment, domestic scene, indoor lighting, comfortable setting, indoor environment, home scene, domestic context, lifestyle photography, comfortable mood"
    },
    "emotional": {
        "happy": "happy expression, joyful mood, positive emotion, cheerful pose, happy atmosphere, positive energy, joyful expression, happy mood, positive lighting, cheerful environment, happy photography, positive mood",
        "serious": "serious expression, contemplative mood, thoughtful pose, serious atmosphere, focused expression, serious mood, contemplative lighting, serious environment, thoughtful photography, focused mood",
        "confident": "confident expression, self-assured pose, confident mood, powerful presence, confident atmosphere, strong expression, confident lighting, powerful environment, confident photography, strong mood"
    },
    "technical": {
        "high_quality": "8K ultra-realistic photography, professional camera settings, sharp focus, detailed features, high resolution, professional quality, crystal clear image, detailed texture, professional lighting, high-end photography, premium quality, professional camera work",
        "cinematic": "cinematic photography, movie-quality lighting, cinematic composition, film-like quality, cinematic atmosphere, professional cinematography, cinematic mood, film-quality camera work, cinematic style, professional film quality",
        "artistic": "artistic photography, creative composition, artistic lighting, creative camera work, artistic quality, creative mood, artistic expression, creative environment, artistic style, creative photography, artistic vision"
    }
}

# Функции для работы с промптами
def get_enhanced_prompt(base_prompt: str, category: str = None, variation: str = None, style: str = None) -> str:
    """
    Создает улучшенный промпт на основе базового.

    Args:
        base_prompt: Базовый промпт пользователя
        category: Категория (portrait, environmental, action, conceptual, fashion)
        variation: Вариация внутри категории
        style: Стиль (professional, casual, creative, etc.)

    Returns:
        Улучшенный промпт
    """
    enhanced_parts = []

    # Добавляем базовый промпт
    enhanced_parts.append(base_prompt)

    # Добавляем профессиональные улучшения
    if category and category in PROFESSIONAL_PROMPTS:
        enhanced_parts.append(PROFESSIONAL_PROMPTS[category]["base"])

        if variation and variation in PROFESSIONAL_PROMPTS[category]["variations"]:
            enhanced_parts.append(PROFESSIONAL_PROMPTS[category]["variations"][variation])

    # Добавляем стилевые улучшения
    if style and style in ENHANCED_PROMPTS:
        for subcategory, prompt in ENHANCED_PROMPTS[style].items():
            if subcategory in base_prompt.lower():
                enhanced_parts.append(prompt)
                break

    # Добавляем технические улучшения
    enhanced_parts.append("8K ultra-realistic, professional photography, sharp focus, natural skin texture, professional camera settings")

    return ", ".join(enhanced_parts)

def analyze_prompt_intent(prompt: str) -> dict:
    """
    Анализирует промпт и определяет намерение пользователя.

    Args:
        prompt: Промпт пользователя

    Returns:
        Словарь с анализом намерения
    """
    prompt_lower = prompt.lower()

    analysis = {
        "category": "general",
        "style": "professional",
        "mood": "neutral",
        "environment": "studio",
        "lighting": "natural",
        "focus": "portrait"
    }

    # Определяем категорию
    if any(word in prompt_lower for word in ["портрет", "лицо", "face", "portrait"]):
        analysis["category"] = "portrait"
    elif any(word in prompt_lower for word in ["мода", "стиль", "fashion", "style", "одежда", "clothing"]):
        analysis["category"] = "fashion"
    elif any(word in prompt_lower for word in ["действие", "движение", "action", "motion", "спорт", "sport"]):
        analysis["category"] = "action"
    elif any(word in prompt_lower for word in ["концепт", "искусство", "concept", "art", "креатив", "creative"]):
        analysis["category"] = "conceptual"
    elif any(word in prompt_lower for word in ["окружение", "среда", "environment", "setting", "фон", "background"]):
        analysis["category"] = "environmental"

    # Определяем стиль
    if any(word in prompt_lower for word in ["бизнес", "деловой", "business", "formal", "официальный"]):
        analysis["style"] = "professional"
    elif any(word in prompt_lower for word in ["повседневный", "casual", "обычный", "relaxed"]):
        analysis["style"] = "casual"
    elif any(word in prompt_lower for word in ["креативный", "creative", "артистичный", "artistic"]):
        analysis["style"] = "creative"

    # Определяем настроение
    if any(word in prompt_lower for word in ["счастливый", "радостный", "happy", "joyful", "веселый"]):
        analysis["mood"] = "happy"
    elif any(word in prompt_lower for word in ["серьезный", "serious", "задумчивый", "thoughtful"]):
        analysis["mood"] = "serious"
    elif any(word in prompt_lower for word in ["уверенный", "confident", "сильный", "strong"]):
        analysis["mood"] = "confident"

    # Определяем окружение
    if any(word in prompt_lower for word in ["город", "urban", "улица", "street", "городской"]):
        analysis["environment"] = "urban"
    elif any(word in prompt_lower for word in ["природа", "nature", "outdoor", "на улице", "лес", "forest"]):
        analysis["environment"] = "nature"
    elif any(word in prompt_lower for word in ["дом", "home", "внутри", "indoor", "комната", "room"]):
        analysis["environment"] = "indoor"

    return analysis

def create_optimized_prompt(user_prompt: str, generation_type: str = "with_avatar") -> str:
    """
    Создает оптимизированный промпт на основе анализа намерения пользователя.

    Args:
        user_prompt: Промпт пользователя
        generation_type: Тип генерации

    Returns:
        Оптимизированный промпт
    """
    # Анализируем намерение
    intent = analyze_prompt_intent(user_prompt)

    # Создаем улучшенный промпт
    enhanced_prompt = get_enhanced_prompt(
        user_prompt,
        category=intent["category"],
        style=intent["style"]
    )

    # Добавляем специфичные улучшения для типа генерации
    if generation_type == "with_avatar":
        enhanced_prompt += ", with personal avatar, identity preservation, consistent facial features"
    elif generation_type == "photo_to_photo":
        enhanced_prompt += ", photo-to-photo transformation, reference image style, style transfer"
    elif generation_type == "ai_video_v2_1":
        enhanced_prompt += ", video generation, motion capture, dynamic movement, cinematic quality"

    return enhanced_prompt
