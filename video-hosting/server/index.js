import express from 'express'
import multer from 'multer'
import cors from 'cors'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'
import { createRequire } from 'module'

const require = createRequire(import.meta.url)
const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Load .env manually (dotenv ESM compat)
const envPath = path.join(__dirname, '..', '.env')
if (fs.existsSync(envPath)) {
  fs.readFileSync(envPath, 'utf8').split('\n').forEach(line => {
    const [k, ...v] = line.split('=')
    if (k && v.length) process.env[k.trim()] = v.join('=').trim()
  })
}

const app = express()
const PORT = process.env.API_PORT || 3001
const API_TOKEN = process.env.API_TOKEN || 'osh1-vh-2026-sk-9f3a'
const UPLOADS_DIR = path.join(__dirname, 'uploads')

if (!fs.existsSync(UPLOADS_DIR)) fs.mkdirSync(UPLOADS_DIR, { recursive: true })

const storage = multer.diskStorage({
  destination: UPLOADS_DIR,
  filename: (req, file, cb) => {
    const unique = Date.now() + '-' + Math.round(Math.random() * 1e9)
    cb(null, unique + path.extname(file.originalname))
  },
})
const upload = multer({
  storage,
  limits: { fileSize: 500 * 1024 * 1024 },
}).any()

const auth = (req, res, next) => {
  const token = req.headers['x-api-token'] || req.query.token
  if (token !== API_TOKEN) return res.status(401).json({ error: 'Unauthorized. Pass X-Api-Token header.' })
  next()
}

app.use(cors())
app.use(express.json())
app.use('/uploads', express.static(UPLOADS_DIR))

// GET /api/videos
app.get('/api/videos', (req, res) => {
  try {
    const files = fs.readdirSync(UPLOADS_DIR).filter(f => f.endsWith('.json'))
    const videos = files.map(f => {
      try { return JSON.parse(fs.readFileSync(path.join(UPLOADS_DIR, f))) }
      catch { return null }
    }).filter(Boolean)
    videos.sort((a, b) => new Date(b.uploadedAt) - new Date(a.uploadedAt))
    res.json({ videos, count: videos.length })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// GET /api/videos/:id
app.get('/api/videos/:id', (req, res) => {
  const meta = path.join(UPLOADS_DIR, req.params.id + '.json')
  if (!fs.existsSync(meta)) return res.status(404).json({ error: 'Not found' })
  res.json(JSON.parse(fs.readFileSync(meta)))
})

// POST /api/videos
app.post('/api/videos', auth, upload, (req, res) => {
  const videoFile = req.files?.find(f => f.fieldname === 'video')
  const thumbFile = req.files?.find(f => f.fieldname === 'thumbnail')
  if (!videoFile) return res.status(400).json({ error: 'No video file in field "video"' })
  const { title, subject, description, transcript, clip_id } = req.body
  const id = clip_id || path.basename(videoFile.filename, path.extname(videoFile.filename))
  const videoData = {
    id,
    title: title || videoFile.originalname.replace(/\.[^.]+$/, ''),
    subject: subject || null,
    description: description || null,
    filename: videoFile.filename,
    originalName: videoFile.originalname,
    size: videoFile.size,
    url: `/uploads/${videoFile.filename}`,
    thumbnailUrl: thumbFile ? `/uploads/${thumbFile.filename}` : null,
    transcript: transcript || null,
    uploadedAt: new Date().toISOString(),
  }
  fs.writeFileSync(path.join(UPLOADS_DIR, id + '.json'), JSON.stringify(videoData, null, 2))
  res.status(201).json(videoData)
})

// DELETE /api/videos/:id
app.delete('/api/videos/:id', auth, (req, res) => {
  const meta = path.join(UPLOADS_DIR, req.params.id + '.json')
  if (!fs.existsSync(meta)) return res.status(404).json({ error: 'Not found' })
  const video = JSON.parse(fs.readFileSync(meta))
  const videoFile = path.join(UPLOADS_DIR, video.filename)
  if (fs.existsSync(videoFile)) fs.unlinkSync(videoFile)
  fs.unlinkSync(meta)
  res.json({ deleted: req.params.id })
})

app.use((err, req, res, next) => {
  if (err.code === 'LIMIT_FILE_SIZE') return res.status(413).json({ error: 'File too large (max 500 MB)' })
  res.status(400).json({ error: err.message })
})

app.listen(PORT, () => {
  console.log(`API server: http://localhost:${PORT}`)
  console.log(`Token:      ${API_TOKEN}`)
})
