# Adding New Story Templates

This guide explains how to create and add new devotional story templates to the DevotionalAI platform.

## Template Format

Each template is a JSON file with the following structure:

```json
{
  "name": "Story Name",
  "description": "Brief description for dashboard",
  "category": "devotional",
  "duration_minutes": 12,
  "language": "hindi",
  "author": "DevotionalAI",
  "scenes": [
    {
      "scene_number": 1,
      "scene_title": "Scene Title",
      "image_prompt": "Detailed AI image generation prompt...",
      "voiceover": "Narration in Hindi/English/Sanskrit...",
      "notes": "Production notes for cinematographers"
    }
    // ... more scenes
  ]
}
```

## Field Descriptions

### Top-level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name in dashboard (30-50 chars recommended) |
| `description` | string | Yes | Summary shown in template list (100-150 chars) |
| `category` | string | Yes | Category: `devotional`, `educational`, `historical`, `mythological` |
| `duration_minutes` | number | Yes | Estimated video length (8-20 minutes typical) |
| `language` | string | Yes | Primary language: `hindi`, `english`, `sanskrit`, `mixed` |
| `author` | string | Yes | Creator attribution |
| `scenes` | array | Yes | Array of scene objects (minimum 6, maximum 20 recommended) |

### Scene Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scene_number` | number | Yes | Sequential numbering (1, 2, 3...) |
| `scene_title` | string | Yes | Chapter title (20-50 chars) |
| `image_prompt` | string | Yes | Detailed prompt for AI image generation (see below) |
| `voiceover` | string | Yes | Narration text in target language |
| `notes` | string | No | Production/technical notes for rendering |

## Writing Effective Image Prompts

Image prompts should be:

1. **Highly Detailed** - Describe characters, clothing, environment, lighting
2. **Cinematic** - Include camera angles, depth, atmospheric effects
3. **Art Style** - Specify style (Raja Ravi Varma, Mughal miniature, photorealistic)
4. **Technical** - Include resolution, quality, and rendering hints

### Example Image Prompt (Bad ❌)

```
A man sitting under a tree
```

### Example Image Prompt (Good ✅)

```
A elderly sage Vashistha with long white beard, wearing orange robes, 
sitting peacefully under an ancient banyan tree by a river, holding 
a wooden staff. Golden evening light filters through the leaves, 
creating dappled shadows. Mountains in misty background. Serene 
meditation pose. Style: semi-realistic Raja Ravi Varma Indian classical 
painting with devotional warmth. Ultra high detail, 4K, cinematic lighting, 
spiritual aura around figure.
```

### Prompt Components

- **Characters**: Age, appearance, clothing, jewelry, pose, expression
- **Environment**: Location, time of day, weather, plants, water, architecture
- **Lighting**: Direction, color, intensity, special effects (glow, aura, particles)
- **Style**: Art style, artistic movement, cinematic techniques
- **Quality**: Resolution, detail level, special effects

## Voice-Over Text Guidelines

### Language Support

- **Hindi**: Use Devanagari script for authenticity
- **English**: Use for translations or mixed content
- **Sanskrit**: Use proper diacritics (ṃ, ṇ, ś, ṛ)
- **Mixed**: Use appropriate script for each language segment

### Writing for TTS

1. **Clarity**: Use complete sentences; avoid fragments
2. **Pacing**: Mark pauses with newlines (`\n`)
3. **Pronunciation**: Add Hindi/Sanskrit text phonetically if needed
4. **Tone**: Specify devotional, reverent, joyful, etc. in notes
5. **Length**: Aim for 8-15 seconds per scene (approximately 40-80 words)

### Example Voice-Over (Good ✅)

```
Prahlad, ek nirmal hriday bachcha, har pal Bhagwan Vishnu ka naam leta aur 
shraddha se pooja karta. Uski bhakti nirmal aur nirantar thi.
```

Breakdown:
- Clear Hindi narration
- Natural pacing
- ~10 seconds duration
- Devotional tone
- Proper Devanagari script

## Production Notes

The `notes` field is for guidance to cinematographers/editors:

```
"notes": "Duration: 10-12s. TTS: warm female, reverent tone. Camera: slow dolly-in. 
Subtitles: 2-3 lines, max 38 chars each. Music: soft devotional instrumental."
```

## Step-by-Step: Create a New Template

### 1. Research Your Story

- Choose a popular Sanatan Dharma story (Ramayana, Mahabharata, Puranas, etc.)
- Outline 6-8 key scenes that capture the essence
- Identify key characters and moral lessons

### 2. Write Scene Descriptions

For each scene, write:
- Scene title (1-3 words)
- Detailed image prompt (2-4 sentences)
- Voice-over narration (40-80 words)
- Production notes (10-20 words)

### 3. Create JSON File

Save as `/platform/templates/story_name.json`:

```bash
cat > /platform/templates/hanuman.json << 'EOF'
{
  "name": "Hanuman - The Devoted Warrior",
  "description": "The remarkable journey of Hanuman from humble devotee to mighty warrior, embodying bhakti and strength.",
  "category": "devotional",
  "duration_minutes": 13,
  "language": "hindi",
  "author": "Your Name",
  "scenes": [
    {
      "scene_number": 1,
      "scene_title": "Hanuman's Birth and Early Life",
      "image_prompt": "Young Hanuman as a playful monkey boy in the forests of the Himalaya...",
      "voiceover": "Hanuman, Vayu devata ke putra, ek bahut balwaan aur tej ek aur bhakti sheel balak the...",
      "notes": "Duration: 10s. Camera: wide establishing shot to close-up. Tone: joyful."
    },
    // ... more scenes
  ]
}
EOF
```

### 4. Validate JSON

```bash
# Check JSON syntax
python -c "import json; json.load(open('/platform/templates/hanuman.json'))"

# Should output nothing if valid; error if invalid
```

### 5. Add Optional Thumbnail

Create 400x300px JPG image:

```bash
# Example using ImageMagick
convert -size 400x300 xc:navy -pointsize 40 -gravity center \
  -fill gold -annotate +0+0 'Hanuman' \
  /platform/templates/thumbnails/hanuman.jpg
```

### 6. Test in Platform

1. Restart backend (to reload templates):
   ```bash
   docker-compose restart backend
   ```

2. Go to Dashboard → Templates
3. Your new template should appear in the list

4. Create a test project with the template:
   - Click "New Project"
   - Select your template
   - Verify all scenes load correctly

## Template Quality Checklist

- [ ] JSON is valid (no syntax errors)
- [ ] At least 6 scenes, max 20
- [ ] Each scene has title, prompt, voiceover
- [ ] Image prompts are detailed and cinematic (200+ chars)
- [ ] Voiceovers are 40-80 words (~8-15 seconds)
- [ ] Total video duration estimates 8-20 minutes
- [ ] Language is authentic (proper script/grammar)
- [ ] Moral/spiritual lesson is clear
- [ ] Thumbnail image is provided (optional but recommended)
- [ ] Tested in dashboard with sample generation

## Built-in Templates (Examples)

The platform includes these templates by default:

1. **Prahlad Bhakt** (8 scenes, 12 min)
   - Story: Young devotee vs. demon father
   - Lesson: Faith triumphs over adversity
   - File: `prahlad.json`

2. **Krishna Leela** (8 scenes, 14 min)
   - Story: Divine play and wisdom
   - Lesson: Devotion, divine love, duty
   - File: `krishna.json`

3. **Hanuman Chalisa** (7 scenes, 11 min - template provided below)
   - Story: Hanuman's journey of devotion
   - Lesson: Bhakti and strength
   - File: `hanuman.json`

## Template: Hanuman Chalisa (Ready to Use)

```json
{
  "name": "Hanuman - The Devoted Warrior",
  "description": "The remarkable journey of Hanuman from humble devotee to mighty warrior. A tale of bhakti, strength, and unwavering loyalty.",
  "category": "devotional",
  "duration_minutes": 13,
  "language": "hindi",
  "author": "DevotionalAI",
  "scenes": [
    {
      "scene_number": 1,
      "scene_title": "Hanuman's Birth - Son of Wind",
      "image_prompt": "Young Hanuman as a playful monkey boy in the misty Himalayan forests, surrounded by ancient cedar trees, morning mist, golden sunrise light. Show his powerful form even as a child. Background: sacred mountain shrine. Lighting: ethereal, divine. Style: semi-realistic mythological art, Raja Ravi Varma influence, ultra-detailed, 4K.",
      "voiceover": "Hanuman, Vayu devata ke putra, ek bahut balwaan aur tej ek aur bhakti sheel balak the. Inhe bachchpan se hi asadharan shakti thi."
    },
    {
      "scene_number": 2,
      "scene_title": "Meeting Lord Rama",
      "image_prompt": "Hanuman kneeling before Lord Rama in the forest of Kishkindha, Rama sitting on a stone with bow, Lakshmana beside him. Hanuman has tears of devotion. Forest background with ancient trees, evening light. Divine aura around Rama. Style: classical, devotional, dramatic lighting.",
      "voiceover": "Jab Hanuman ne Prabhu Rama ko dekha, unhe turant sampurn prema ka anubhav hua. Unhe apna jeevan samarpit kar diya."
    },
    {
      "scene_number": 3,
      "scene_title": "The Leap Across the Ocean",
      "image_prompt": "Hanuman in heroic mid-air leap over the vast Arabian Sea, his body extending across the ocean, powerful muscular form, determination on face. Below: roaring ocean waves, islands, sky above with celestial light. Style: epic, heroic, action-packed, ultra-detailed 4K.",
      "voiceover": "Prabhu ke sankat ko dur karne ke liye Hanuman ne samudra ko langen ka sangkalp kiya. Unhe Rama ka naam hi shakti tha."
    },
    {
      "scene_number": 4,
      "scene_title": "Lanka Reconnaissance",
      "image_prompt": "Hanuman entering the golden city of Lanka at night, cautiously moving through palaces, sophisticated urban setting with towers and walls, moonlit. Show Hanuman's intelligence and strength balanced. Background: demon guards patrolling. Style: cinematic, dramatic, detailed.",
      "voiceover": "Lanka mein Hanuman ne Sita Mata ko khoja. Har jagah dekha, hamesha Rama ka naam letin rahe."
    },
    {
      "scene_number": 5,
      "scene_title": "Hanuman's Strength - Tail Destruction",
      "image_prompt": "Hanuman with his powerful tail destroying demon armies in Lanka, epic battle scene, explosions of divine power, demons fleeing, Hanuman radiant with strength. Show his tail like a weapon. Style: action epic, heroic, semi-realistic, high detail.",
      "voiceover": "Jab Hanuman ne apni shakti prakash ki, sab demon bhag gaye. Inhe koi rok na saka. Yahi tha bhakti ki asadharan shakti."
    },
    {
      "scene_number": 6,
      "scene_title": "Sanjeevani Mountain",
      "image_prompt": "Hanuman carrying the entire Sanjeevani mountain on his palm, flying back to Lanka through the night sky, stars visible, moonlight on mountain, divine glow. Below: ocean and islands. Style: magical, epic, surreal, 4K.",
      "voiceover": "Lakshmana ke jeevit karne ke liye Hanuman ne poora Sanjeevani parvat le aaya. Bhakti mein sab sambhav tha."
    },
    {
      "scene_number": 7,
      "scene_title": "Eternal Devotion",
      "image_prompt": "Hanuman in temple, meditating peacefully, Rama and Sita above in divine form blessing him. Soft golden temple lights, flowers, incense smoke, sacred atmosphere. Hanuman's serene, devoted expression. Style: spiritual, devotional masterpiece, warm golden lighting.",
      "voiceover": "Hanuman, Prabhu ke sache bhakt aaj bhi poori duniya mein puja jaate hain. Unka naam hi bhakti ki misaal hai. Jai Hanuman!"
    }
  ]
}
```

## Submitting Templates to Community

1. **Fork the repo** on GitHub
2. **Add your template** in `/platform/templates/`
3. **Create a pull request** with:
   - JSON file
   - Brief description
   - Thumbnail image (optional)
4. **Wait for review** - maintainers will test and merge

---

## Tips for Success

1. **Start Simple** - Begin with 6-8 scenes; expand later
2. **Use Authentic Language** - Proper Hindi/Sanskrit adds authenticity
3. **Balance Detail** - Enough for imagination, not so much it slows generation
4. **Test Thoroughly** - Run through complete pipeline before publishing
5. **Get Feedback** - Share with community for improvements
6. **Keep Updated** - Improve templates based on user feedback

---

## Support

- **Template Issues**: GitHub Issues (tag `template`)
- **Email**: templates@devotionalai.example.com
- **Community Discord**: Share and discuss templates

Happy creating! 🙏📖
