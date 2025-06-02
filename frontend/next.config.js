
const nextConfig = {
  transpilePackages: ["three"],
  reactStrictMode: false,
  webpack: config => {
    config.resolve.fallback = {fs: false};
    config.module.rules.push({
     
      test:/\.svg$/,
      use: ["@svgr/webpack"]
    })
    
    return config;
  }
};

module.exports = nextConfig;
