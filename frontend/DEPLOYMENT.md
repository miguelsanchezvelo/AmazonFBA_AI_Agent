# Frontend Deployment Guide

## 🚀 Quick Start (Development)

### Windows
```bash
START_FRONTEND.bat
```

### Linux/Mac
```bash
npm install
npm run dev
```

The app will be available at `http://localhost:5173`

## 📦 Production Build

### 1. Build the application

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

### 2. Preview the build locally

```bash
npm run preview
```

## 🌐 Deployment Options

### Option 1: Vercel (Recommended)

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Deploy:
```bash
vercel --prod
```

### Option 2: Netlify

1. Install Netlify CLI:
```bash
npm install -g netlify-cli
```

2. Build and deploy:
```bash
npm run build
netlify deploy --prod --dir=dist
```

### Option 3: Docker

1. Create `Dockerfile` in frontend root:

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

2. Create `nginx.conf`:

```nginx
server {
    listen 80;
    location / {
        root /usr/share/nginx/html;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }
}
```

3. Build and run:

```bash
docker build -t fba-frontend .
docker run -p 3000:80 fba-frontend
```

### Option 4: AWS S3 + CloudFront

1. Build the app:
```bash
npm run build
```

2. Upload to S3:
```bash
aws s3 sync dist/ s3://your-bucket-name --delete
```

3. Create CloudFront distribution pointing to the S3 bucket

4. Set up custom domain (optional)

## ⚙️ Environment Configuration

### Development
Create `.env` file:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_ENV=development
```

### Production
Create `.env.production` file:
```env
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com/ws
VITE_ENV=production
```

## 🔒 Security Checklist

- [ ] Environment variables configured correctly
- [ ] API endpoints use HTTPS in production
- [ ] WebSocket uses WSS in production
- [ ] CORS configured on backend
- [ ] CSP headers configured
- [ ] Authentication tokens secured
- [ ] No sensitive data in client code

## 📊 Performance Optimization

### Code Splitting
Already configured with Vite's automatic code splitting.

### Image Optimization
Use optimized images:
- WebP format
- Lazy loading
- Responsive images

### Bundle Analysis
```bash
npm run build -- --analyze
```

## 🧪 Testing Before Deploy

1. Run linter:
```bash
npm run lint
```

2. Build production:
```bash
npm run build
```

3. Test production build:
```bash
npm run preview
```

4. Check all pages work
5. Test dark mode toggle
6. Verify API connections
7. Test WebSocket real-time updates
8. Check responsive design on mobile

## 📈 Monitoring

### Setup Analytics

Add to `index.html`:
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

### Error Monitoring

Consider integrating:
- Sentry
- LogRocket
- Rollbar

## 🔄 CI/CD Pipeline

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Frontend

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm install
        
      - name: Build
        run: npm run build
        env:
          VITE_API_BASE_URL: ${{ secrets.API_URL }}
          VITE_WS_URL: ${{ secrets.WS_URL }}
      
      - name: Deploy to Vercel
        run: vercel --prod --token=${{ secrets.VERCEL_TOKEN }}
```

## 🐛 Troubleshooting

### Build fails
```bash
rm -rf node_modules package-lock.json
npm install
npm run build
```

### WebSocket not connecting
- Check WSS vs WS protocol
- Verify backend WebSocket server
- Check firewall/proxy settings

### Blank page after deployment
- Check browser console for errors
- Verify base URL in vite.config.ts
- Check routing configuration

## 📝 Deployment Checklist

- [ ] Code builds without errors
- [ ] All tests pass
- [ ] Environment variables set
- [ ] API endpoints configured
- [ ] WebSocket URL configured
- [ ] HTTPS/WSS enabled
- [ ] Domain configured (if applicable)
- [ ] Analytics set up
- [ ] Error monitoring enabled
- [ ] Performance tested
- [ ] Mobile responsiveness verified
- [ ] Dark mode works
- [ ] All pages accessible

## 🎉 Post-Deployment

1. Test all functionality in production
2. Monitor error logs
3. Check performance metrics
4. Set up alerts for downtime
5. Document deployment process
6. Train team on deployment

## 📞 Support

For deployment issues:
1. Check logs in browser console
2. Verify environment variables
3. Test API connectivity
4. Check backend status

## 📚 Resources

- [Vite Deployment Docs](https://vitejs.dev/guide/static-deploy.html)
- [Vercel Docs](https://vercel.com/docs)
- [Netlify Docs](https://docs.netlify.com/)
- [AWS S3 Static Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)

