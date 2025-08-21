# Procur Frontend

A modern React frontend for the Procur Group Purchasing Organization platform.

## Features

- 🔐 **Authentication System** - Secure login and registration with JWT tokens
- 📊 **Dashboard** - Overview of groups, invitations, and activity
- 👥 **Group Management** - Create, join, and manage purchasing groups
- 📧 **Invitation System** - Send and manage group invitations
- 🎨 **Modern UI** - Beautiful Material-UI design with responsive layout
- 📱 **Mobile Responsive** - Works seamlessly on all devices
- 🔒 **Protected Routes** - Secure access to authenticated features

## Tech Stack

- **React 18** - Modern React with hooks
- **TypeScript** - Type-safe development
- **Material-UI (MUI)** - Beautiful and consistent UI components
- **React Router** - Client-side routing
- **Axios** - HTTP client for API communication
- **React Query** - Data fetching and caching
- **Context API** - State management

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- Backend API running (see backend documentation)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd procur-frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create environment variables:
Create a `.env` file in the root directory:
```env
REACT_APP_API_URL=http://localhost:8000/api
```

4. Start the development server:
```bash
npm start
```

The application will be available at `http://localhost:3000`.

### Available Scripts

- `npm start` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Navigation.tsx   # Main navigation component
│   └── ProtectedRoute.tsx # Authentication wrapper
├── contexts/           # React contexts
│   └── AuthContext.tsx # Authentication state management
├── pages/              # Page components
│   ├── LoginPage.tsx   # Login page
│   ├── RegisterPage.tsx # Registration page
│   └── DashboardPage.tsx # Main dashboard
├── services/           # API services
│   └── api.ts         # API client and endpoints
├── types/              # TypeScript type definitions
│   └── index.ts       # All type definitions
├── hooks/              # Custom React hooks
├── utils/              # Utility functions
└── App.tsx            # Main application component
```

## API Integration

The frontend communicates with the backend API through the `apiService` in `src/services/api.ts`. The service includes:

- Authentication endpoints (login, register, logout)
- User management
- Group operations
- Invitation handling
- File uploads

## Authentication Flow

1. User visits login/register page
2. Credentials are validated against the backend
3. JWT tokens are stored in localStorage
4. Protected routes check authentication status
5. Automatic token refresh and logout on expiration

## Styling

The application uses Material-UI with a custom theme that includes:

- Custom color palette
- Typography overrides
- Component style customizations
- Responsive design breakpoints

## Development

### Adding New Pages

1. Create a new component in `src/pages/`
2. Add the route to `App.tsx`
3. Update navigation if needed

### Adding New Components

1. Create the component in `src/components/`
2. Export it from the components index
3. Import and use in pages

### API Integration

1. Add new endpoints to `src/services/api.ts`
2. Create corresponding types in `src/types/index.ts`
3. Use React Query for data fetching

## Deployment

### Build for Production

```bash
npm run build
```

This creates a `build` folder with optimized production files.

### Environment Variables

Set the following environment variables for production:

- `REACT_APP_API_URL` - Backend API URL

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.
