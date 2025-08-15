# Trade Manthan - React Frontend

A modern, high-performance React frontend for the Trade Manthan crypto trading platform, built with TypeScript, Tailwind CSS, and modern React patterns.

## 🚀 Features

- **Modern React 18** with TypeScript for type safety
- **Responsive Design** with mobile-first approach
- **Dark/Light Theme** with system preference detection
- **Performance Optimized** with lazy loading and code splitting
- **Accessibility** compliant with ARIA standards
- **Real-time Updates** with React Query for data management
- **Smooth Animations** with Framer Motion
- **Modern UI Components** with Tailwind CSS and Lucide icons

## 🛠️ Tech Stack

### Core Technologies
- **React 18** - Latest React with concurrent features
- **TypeScript** - Type-safe development
- **React Router 6** - Modern routing solution
- **Tailwind CSS** - Utility-first CSS framework

### State Management & Data Fetching
- **React Query** - Server state management and caching
- **React Context** - Client state management
- **Axios** - HTTP client with interceptors

### UI & UX
- **Framer Motion** - Smooth animations and transitions
- **Lucide React** - Beautiful, customizable icons
- **React Hook Form** - Performant forms with validation
- **React Hot Toast** - Elegant notifications

### Development Tools
- **ESLint** - Code linting and quality
- **Prettier** - Code formatting
- **PostCSS** - CSS processing
- **Autoprefixer** - CSS vendor prefixing

## 📁 Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Layout/         # Layout components (Header, Sidebar)
│   └── UI/            # Common UI components
├── contexts/           # React Context providers
├── hooks/             # Custom React hooks
├── pages/             # Page components
├── services/          # API services
├── types/             # TypeScript type definitions
├── utils/             # Utility functions
├── App.tsx            # Main app component
├── index.tsx          # App entry point
└── index.css          # Global styles
```

## 🚀 Getting Started

### Prerequisites

- Node.js 16+ 
- npm or yarn
- Modern browser with ES6+ support

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd crypto_trading_1
   ```

2. **Install dependencies**
   ```bash
   npm install
   # or
   yarn install
   ```

3. **Start development server**
   ```bash
   npm start
   # or
   yarn start
   ```

4. **Open your browser**
   Navigate to `http://localhost:3000`

### Build for Production

```bash
npm run build
# or
yarn build
```

The build artifacts will be stored in the `build/` directory.

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
REACT_APP_API_URL=http://localhost:5000
REACT_APP_APP_NAME=Trade Manthan
REACT_APP_VERSION=1.0.0
```

### Tailwind Configuration

The Tailwind CSS configuration is in `tailwind.config.js` with custom:
- Color palette
- Typography scales
- Animation keyframes
- Custom utilities

## 📱 Pages & Features

### 1. **Login Page** (`/login`)
- Modern authentication interface
- Social login options
- Form validation with React Hook Form
- Responsive design for all devices

### 2. **Dashboard** (`/dashboard`)
- Portfolio overview with key metrics
- Interactive charts with Recharts
- Real-time trading data
- Quick action buttons

### 3. **Strategy Management** (`/strategy`)
- Strategy overview and statistics
- Strategy table with actions
- Performance metrics
- **Note: Add/Edit section removed as requested**

### 4. **Trading History** (`/history`)
- Comprehensive trade history
- Advanced filtering and search
- Export functionality
- Performance analytics

### 5. **Settings** (`/settings`)
- User profile management
- Security settings
- Notification preferences
- Theme and language options

## 🎨 Design System

### Color Palette
- **Primary**: Blue shades for main actions
- **Success**: Green for positive states
- **Warning**: Yellow/Orange for caution
- **Danger**: Red for errors/destructive actions
- **Neutral**: Gray scale for text and backgrounds

### Typography
- **Font Family**: Inter (primary), JetBrains Mono (monospace)
- **Scale**: Consistent sizing from xs to 6xl
- **Weights**: 300, 400, 500, 600, 700, 800

### Components
- **Buttons**: Primary, secondary, danger variants
- **Cards**: Consistent elevation and spacing
- **Forms**: Accessible input fields with validation
- **Tables**: Responsive data tables
- **Modals**: Overlay dialogs with animations

## 🔒 Security Features

- **JWT Authentication** with secure token storage
- **Route Protection** for authenticated users
- **CSRF Protection** with proper headers
- **Input Validation** on both client and server
- **Secure API Calls** with interceptors

## 📊 Performance Optimizations

### Code Splitting
- **Lazy Loading** for route components
- **Dynamic Imports** for heavy libraries
- **Bundle Analysis** with webpack-bundle-analyzer

### Caching Strategy
- **React Query** for server state caching
- **Local Storage** for user preferences
- **Service Worker** for offline support (future)

### Rendering Optimizations
- **React.memo** for expensive components
- **useCallback/useMemo** for stable references
- **Virtual Scrolling** for large lists (future)

## 🧪 Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

## 📝 Code Quality

### Linting & Formatting
```bash
# Lint code
npm run lint

# Fix linting issues
npm run lint:fix

# Format code
npm run format

# Type checking
npm run type-check
```

### Git Hooks
- Pre-commit linting
- Pre-push type checking
- Commit message validation

## 🌐 Browser Support

- **Chrome** 90+
- **Firefox** 88+
- **Safari** 14+
- **Edge** 90+

## 📱 Responsive Design

- **Mobile First** approach
- **Breakpoints**: sm (640px), md (768px), lg (1024px), xl (1280px)
- **Touch Friendly** interactions
- **Progressive Enhancement**

## 🚀 Deployment

### Build Process
1. Run `npm run build`
2. Test the build locally with `npm run serve`
3. Deploy the `build/` folder to your hosting service

### Environment Setup
- Set production environment variables
- Configure API endpoints
- Enable HTTPS
- Set up CDN for static assets

## 🔄 Development Workflow

1. **Feature Development**
   - Create feature branch from `main`
   - Implement with TypeScript and tests
   - Follow component design patterns
   - Update documentation

2. **Code Review**
   - Submit pull request
   - Ensure all tests pass
   - Code quality checks
   - Performance review

3. **Deployment**
   - Merge to main branch
   - Automated build and test
   - Staging deployment
   - Production deployment

## 📚 Additional Resources

- [React Documentation](https://reactjs.org/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Framer Motion Guide](https://www.framer.com/motion/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review existing issues and solutions

---

**Built with ❤️ using modern web technologies**
