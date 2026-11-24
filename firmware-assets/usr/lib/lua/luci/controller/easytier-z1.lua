-- LuCI app: EasyTier — 图形界面外壳，数据来自 z1 CGI (/www/cgi-bin/et)
-- 接管旧 luci-app-easytier 的菜单路径 /admin/vpn/easytier，避免遗留菜单 404
module("luci.controller.easytier-z1", package.seeall)

function index()
	entry({"admin", "vpn"}, firstchild(), "VPN", 45).dependent = false
	-- 主菜单：沿用旧插件路径与名称，浏览器缓存的旧菜单点进来也能直达
	entry({"admin", "vpn", "easytier"}, firstchild(), "EasyTier", 46).dependent = true
	entry({"admin", "vpn", "easytier", "status"}, template("easytier-z1/status"), "状态", 1).leaf = true
	entry({"admin", "vpn", "easytier", "config"}, template("easytier-z1/config"), "配置", 2).leaf = true
	entry({"admin", "vpn", "easytier", "log"}, template("easytier-z1/log"), "日志", 3).leaf = true
	-- 兼容旧的 z1 直达链接（不在菜单显示）
	entry({"admin", "vpn", "easytier-z1"}, alias("admin", "vpn", "easytier", "status"), "EasyTier (z1)", 47).hidden = true
	entry({"admin", "vpn", "easytier-z1", "status"}, alias("admin", "vpn", "easytier", "status"), "状态", 1).hidden = true
	entry({"admin", "vpn", "easytier-z1", "config"}, alias("admin", "vpn", "easytier", "config"), "配置", 2).hidden = true
	entry({"admin", "vpn", "easytier-z1", "log"}, alias("admin", "vpn", "easytier", "log"), "日志", 3).hidden = true
end
