const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: [],
  devServer: {
    host: '0.0.0.0',
    port: 8080,
    allowedHosts: 'all'
  },
  // Disable cache for development if cache-loader causes issues
  chainWebpack: config => {
    if (process.env.NODE_ENV === 'development') {
      config.module.rule('js').uses.delete('cache-loader')
      config.module.rule('vue').uses.delete('cache-loader')
    }
  }
})
