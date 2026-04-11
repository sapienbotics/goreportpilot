import { MetadataRoute } from 'next'

// Evaluated once at build time, NOT per request. Calling `new Date()` inside
// the sitemap() function makes every URL report lastModified = <right now>,
// which misleads Googlebot into thinking every page changed on every crawl
// and harms crawl-budget prioritisation.
const BUILD_DATE = new Date()
const BASE_URL = 'https://goreportpilot.com'

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: BASE_URL,                lastModified: BUILD_DATE, changeFrequency: 'weekly',  priority: 1.0 },
    { url: `${BASE_URL}/signup`,    lastModified: BUILD_DATE, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE_URL}/login`,     lastModified: BUILD_DATE, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${BASE_URL}/contact`,   lastModified: BUILD_DATE, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${BASE_URL}/privacy`,   lastModified: BUILD_DATE, changeFrequency: 'yearly',  priority: 0.3 },
    { url: `${BASE_URL}/terms`,     lastModified: BUILD_DATE, changeFrequency: 'yearly',  priority: 0.3 },
    { url: `${BASE_URL}/refund`,    lastModified: BUILD_DATE, changeFrequency: 'yearly',  priority: 0.3 },
  ]
}
