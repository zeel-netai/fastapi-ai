routes_data = [
    {
        "routePath": "/msp-site-wise-alerts",
        "pagePurpose": "Renders the msp site wise alerts view for this application. Users can interact with visualizations and drill into related details.",
        "routeParameters": {
            "key": {
                "purpose": "Optional search/filter key used to narrow down results in list/table views.",
                "type": "uuid",
                "required": "False",
                "source": "queryParam",
            }
        },
        "isDynamicRoute": "False",
        "layouts": ["layout.jsx", "(dashboard)/layout.jsx"],
        "routeGroups": ["dashboard"],
        "accessLevel": "public",
        "id": 1,
    }
]
