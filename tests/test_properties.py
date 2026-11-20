
def test_landlord_can_create_property(client):

    # 1. Register a landlord.
    registration_response = client.post(
        "/auth/register",
        json={
            "full_name": "Test Landlord",
            "email": "landlord@propertytest.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    assert registration_response.status_code == 201

    # 2. Log in as the landlord.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "landlord@propertytest.com",
            "password": "PrimeStay123!"
        }
    )

    assert login_response.status_code == 200

    landlord_id = login_response.get_json()["user"]["id"]

    # 3. Create a property.
    property_response = client.post(
        "/api/properties",
        json={
            "property_name": "Sunrise Residency",
            "property_type": "apartment",
            "address_line": "Vijay Nagar",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452010",
            "bedrooms": 2,
            "bathrooms": 2,
            "description": "A spacious two-bedroom apartment."
        }
    )

    # 4. Verify successful property creation.
    assert property_response.status_code == 201

    result = property_response.get_json()

    assert result["message"] == "Property created successfully."

    assert result["property"]["property_name"] == "Sunrise Residency"

    # 5. Verify automatic ownership assignment.
    assert result["property"]["landlord_id"] == landlord_id


def test_tenant_cannot_create_property(client):

    # Register a tenant.
    registration_response = client.post(
        "/auth/register",
        json={
            "full_name": "Test Tenant",
            "email": "tenant@propertytest.com",
            "password": "PrimeStay123!",
            "role": "tenant"
        }
    )

    assert registration_response.status_code == 201

    # Log in as the tenant.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "tenant@propertytest.com",
            "password": "PrimeStay123!"
        }
    )

    assert login_response.status_code == 200

    # Attempt to create a property.
    response = client.post(
        "/api/properties",
        json={
            "property_name": "Unauthorized Apartment",
            "property_type": "apartment",
            "address_line": "Vijay Nagar",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452010"
        }
    )

    # A tenant should receive HTTP 403 Forbidden.
    assert response.status_code == 403
    
def test_unauthenticated_user_cannot_create_property(client):

    response = client.post(
        "/api/properties",
        json={
            "property_name": "Unauthorized Apartment",
            "property_type": "apartment",
            "address_line": "Vijay Nagar",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452010"
        }
    )

    # An unauthenticated user should receive HTTP 401.
    assert response.status_code == 401
    
    
def test_invalid_property_type_is_rejected(client):

    # Register a landlord.
    client.post(
        "/auth/register",
        json={
            "full_name": "Validation Landlord",
            "email": "validation@propertytest.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    # Log in.
    client.post(
        "/auth/login",
        json={
            "email": "validation@propertytest.com",
            "password": "PrimeStay123!"
        }
    )

    # Submit an invalid property type.
    response = client.post(
        "/api/properties",
        json={
            "property_name": "Test Property",
            "property_type": "hotel",
            "address_line": "Vijay Nagar",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452010"
        }
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == (
        "Property type must be apartment or house."
    )
    
def test_missing_required_property_fields_are_rejected(client):

    # Register a landlord.
    client.post(
        "/auth/register",
        json={
            "full_name": "Missing Field Landlord",
            "email": "missing@propertytest.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    # Log in.
    client.post(
        "/auth/login",
        json={
            "email": "missing@propertytest.com",
            "password": "PrimeStay123!"
        }
    )

    # Submit incomplete property information.
    response = client.post(
        "/api/properties",
        json={
            "property_name": "Incomplete Property",
            "property_type": "apartment"
        }
    )

    assert response.status_code == 400
    assert "address_line" in response.get_json()["error"]
    
def test_negative_bedroom_count_is_rejected(client):

    # Register a landlord.
    client.post(
        "/auth/register",
        json={
            "full_name": "Bedroom Test Landlord",
            "email": "bedroom@propertytest.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    # Log in.
    client.post(
        "/auth/login",
        json={
            "email": "bedroom@propertytest.com",
            "password": "PrimeStay123!"
        }
    )

    # Submit a negative bedroom count.
    response = client.post(
        "/api/properties",
        json={
            "property_name": "Invalid Apartment",
            "property_type": "apartment",
            "address_line": "Vijay Nagar",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452010",
            "bedrooms": -2,
            "bathrooms": 2
        }
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == (
        "bedrooms cannot be negative."
    )
    
    
def test_client_cannot_assign_property_to_another_landlord(client):

    # Register Landlord A.
    client.post(
        "/auth/register",
        json={
            "full_name": "Landlord A",
            "email": "landlord.a@propertytest.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    login_a = client.post(
        "/auth/login",
        json={
            "email": "landlord.a@propertytest.com",
            "password": "PrimeStay123!"
        }
    )

    landlord_a_id = login_a.get_json()["user"]["id"]

    # Log out Landlord A.
    client.post("/auth/logout")

    # Register Landlord B.
    client.post(
        "/auth/register",
        json={
            "full_name": "Landlord B",
            "email": "landlord.b@propertytest.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    # Log in Landlord B.
    login_b = client.post(
        "/auth/login",
        json={
            "email": "landlord.b@propertytest.com",
            "password": "PrimeStay123!"
        }
    )

    landlord_b_id = login_b.get_json()["user"]["id"]

    # Landlord B tries to assign the property to Landlord A.
    response = client.post(
        "/api/properties",
        json={
            "property_name": "Landlord B Apartment",
            "property_type": "apartment",
            "address_line": "Vijay Nagar",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452010",
            "landlord_id": landlord_a_id
        }
    )

    assert response.status_code == 201

    result = response.get_json()

    # Ownership must belong to Landlord B.
    assert result["property"]["landlord_id"] == landlord_b_id

    assert result["property"]["landlord_id"] != landlord_a_id
    

def test_landlord_can_view_own_properties(client):

    # 1. Register a landlord.
    client.post(
        "/auth/register",
        json={
            "full_name": "Property Owner",
            "email": "owner@gettest.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    # 2. Log in as the landlord.
    client.post(
        "/auth/login",
        json={
            "email": "owner@gettest.com",
            "password": "PrimeStay123!"
        }
    )

    # 3. Create the first property.
    client.post(
        "/api/properties",
        json={
            "property_name": "Sunrise Residency",
            "property_type": "apartment",
            "address_line": "Vijay Nagar",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452010",
            "bedrooms": 2,
            "bathrooms": 2
        }
    )

    # 4. Create the second property.
    client.post(
        "/api/properties",
        json={
            "property_name": "Green Villa",
            "property_type": "house",
            "address_line": "Scheme 54",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452011",
            "bedrooms": 3,
            "bathrooms": 2
        }
    )

    # 5. Request all properties.
    response = client.get("/api/properties")

    # 6. Verify the response.
    assert response.status_code == 200

    result = response.get_json()

    assert result["count"] == 2
    assert len(result["properties"]) == 2

    # 7. Verify both property names.
    property_names = [
        property["property_name"]
        for property in result["properties"]
    ]

    assert "Sunrise Residency" in property_names
    assert "Green Villa" in property_names


def test_landlord_cannot_view_another_landlords_properties(client):

    # Register Landlord A.
    client.post(
        "/auth/register",
        json={
            "full_name": "Landlord A",
            "email": "landlord.a@gettest.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    # Log in Landlord A.
    client.post(
        "/auth/login",
        json={
            "email": "landlord.a@gettest.com",
            "password": "PrimeStay123!"
        }
    )

    # Landlord A creates a property.
    client.post(
        "/api/properties",
        json={
            "property_name": "Sunrise Residency",
            "property_type": "apartment",
            "address_line": "Vijay Nagar",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452010"
        }
    )

    # Log out Landlord A.
    client.post("/auth/logout")

    # Register Landlord B.
    client.post(
        "/auth/register",
        json={
            "full_name": "Landlord B",
            "email": "landlord.b@gettest.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    # Log in Landlord B.
    client.post(
        "/auth/login",
        json={
            "email": "landlord.b@gettest.com",
            "password": "PrimeStay123!"
        }
    )

    # Landlord B creates a property.
    client.post(
        "/api/properties",
        json={
            "property_name": "Green Villa",
            "property_type": "house",
            "address_line": "Scheme 54",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452011"
        }
    )

    # Log out Landlord B.
    client.post("/auth/logout")

    # Log in Landlord A again.
    client.post(
        "/auth/login",
        json={
            "email": "landlord.a@gettest.com",
            "password": "PrimeStay123!"
        }
    )

    # Landlord A requests their properties.
    response = client.get("/api/properties")

    assert response.status_code == 200

    result = response.get_json()

    # Landlord A should see only one property.
    assert result["count"] == 1

    property_names = [
        property["property_name"]
        for property in result["properties"]
    ]

    assert "Sunrise Residency" in property_names
    assert "Green Villa" not in property_names


def test_landlord_can_view_own_property(client):

    # Register a landlord.
    client.post(
        "/auth/register",
        json={
            "full_name": "Property Owner",
            "email": "singleproperty@test.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    # Log in.
    client.post(
        "/auth/login",
        json={
            "email": "singleproperty@test.com",
            "password": "PrimeStay123!"
        }
    )

    # Create a property.
    create_response = client.post(
        "/api/properties",
        json={
            "property_name": "Sunrise Residency",
            "property_type": "apartment",
            "address_line": "Vijay Nagar",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452010",
            "bedrooms": 2,
            "bathrooms": 2
        }
    )

    assert create_response.status_code == 201

    property_id = create_response.get_json()["property"]["id"]

    # Retrieve the specific property.
    response = client.get(f"/api/properties/{property_id}")

    assert response.status_code == 200

    result = response.get_json()

    assert result["property"]["id"] == property_id
    assert result["property"]["property_name"] == "Sunrise Residency"
    assert result["property"]["city"] == "Indore"


def test_landlord_cannot_view_another_landlords_property(client):

    # Register Landlord A.
    client.post(
        "/auth/register",
        json={
            "full_name": "Landlord A",
            "email": "landlord.a@singleproperty.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    # Log in Landlord A.
    client.post(
        "/auth/login",
        json={
            "email": "landlord.a@singleproperty.com",
            "password": "PrimeStay123!"
        }
    )

    # Landlord A creates a property.
    create_response = client.post(
        "/api/properties",
        json={
            "property_name": "Sunrise Residency",
            "property_type": "apartment",
            "address_line": "Vijay Nagar",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452010"
        }
    )

    property_id = create_response.get_json()["property"]["id"]

    # Log out Landlord A.
    client.post("/auth/logout")

    # Register Landlord B.
    client.post(
        "/auth/register",
        json={
            "full_name": "Landlord B",
            "email": "landlord.b@singleproperty.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    # Log in Landlord B.
    client.post(
        "/auth/login",
        json={
            "email": "landlord.b@singleproperty.com",
            "password": "PrimeStay123!"
        }
    )

    # Landlord B attempts to access Landlord A's property.
    response = client.get(
        f"/api/properties/{property_id}"
    )

    # The property must not be accessible.
    assert response.status_code == 404

    assert response.get_json()["error"] == "Property not found."


def test_landlord_can_update_own_property(client):

    # 1. Register a landlord.
    client.post(
        "/auth/register",
        json={
            "full_name": "Update Test Landlord",
            "email": "update@propertytest.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    # 2. Log in.
    client.post(
        "/auth/login",
        json={
            "email": "update@propertytest.com",
            "password": "PrimeStay123!"
        }
    )

    # 3. Create a property.
    create_response = client.post(
        "/api/properties",
        json={
            "property_name": "Old Residency",
            "property_type": "apartment",
            "address_line": "Vijay Nagar",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452010",
            "bedrooms": 2,
            "bathrooms": 1
        }
    )

    assert create_response.status_code == 201

    property_id = create_response.get_json()["property"]["id"]

    # 4. Update the property.
    update_response = client.patch(
        f"/api/properties/{property_id}",
        json={
            "property_name": "New Residency",
            "bedrooms": 3,
            "description": "A renovated three-bedroom apartment."
        }
    )

    # 5. Verify successful update.
    assert update_response.status_code == 200

    result = update_response.get_json()

    assert result["message"] == "Property updated successfully."
    assert result["property"]["property_name"] == "New Residency"
    assert result["property"]["bedrooms"] == 3
    assert result["property"]["description"] == (
        "A renovated three-bedroom apartment."
    )

    # 6. Verify unchanged fields remain unchanged.
    assert result["property"]["bathrooms"] == 1
    assert result["property"]["city"] == "Indore"

def test_landlord_cannot_update_another_landlords_property(client):
    # Register the first landlord.
    client.post("/auth/register", json={
        "full_name": "First Landlord",
        "email": "firstupdate@propertytest.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "firstupdate@propertytest.com",
        "password": "PrimeStay123!"
    })

    # First landlord creates a property.
    create_response = client.post("/api/properties", json={
        "property_name": "First Landlord House",
        "property_type": "house",
        "address_line": "Vijay Nagar",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452010"
    })

    property_id = create_response.get_json()["property"]["id"]

    # Log out the first landlord.
    client.post("/auth/logout")

    # Register and log in as a second landlord.
    client.post("/auth/register", json={
        "full_name": "Second Landlord",
        "email": "secondupdate@propertytest.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "secondupdate@propertytest.com",
        "password": "PrimeStay123!"
    })

    # Attempt to update the first landlord's property.
    update_response = client.patch(
        f"/api/properties/{property_id}",
        json={
            "property_name": "Hacked Property"
        }
    )

    assert update_response.status_code == 404
    
def test_landlord_can_deactivate_own_property(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Delete Test Landlord",
        "email": "delete@propertytest.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in.
    client.post("/auth/login", json={
        "email": "delete@propertytest.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    create_response = client.post("/api/properties", json={
        "property_name": "Temporary Residency",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    assert create_response.status_code == 201

    property_id = create_response.get_json()["property"]["id"]

    # Deactivate the property.
    delete_response = client.delete(
        f"/api/properties/{property_id}"
    )

    assert delete_response.status_code == 200

    result = delete_response.get_json()

    assert result["message"] == "Property deactivated successfully."
    assert result["property_id"] == property_id
    assert result["is_active"] is False
    
def test_landlord_sees_only_active_properties_by_default(client):
    # Register and log in a landlord.
    client.post("/auth/register", json={
        "full_name": "Filter Test Landlord",
        "email": "filter@propertytest.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "filter@propertytest.com",
        "password": "PrimeStay123!"
    })

    # Create two properties.
    first_response = client.post("/api/properties", json={
        "property_name": "Active Residency",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    second_response = client.post("/api/properties", json={
        "property_name": "Inactive Residency",
        "property_type": "house",
        "address_line": "Vijay Nagar",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452010"
    })

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    # Deactivate the second property.
    inactive_id = second_response.get_json()["property"]["id"]

    delete_response = client.delete(
        f"/api/properties/{inactive_id}"
    )

    assert delete_response.status_code == 200

    # Retrieve properties without specifying a status.
    response = client.get("/api/properties")

    assert response.status_code == 200

    result = response.get_json()

    assert result["count"] == 1
    assert result["properties"][0]["property_name"] == "Active Residency"
    assert result["properties"][0]["is_active"] is True
    
    
def test_landlord_can_filter_inactive_properties(client):
    # Register and log in a landlord.
    client.post("/auth/register", json={
        "full_name": "Inactive Filter Landlord",
        "email": "inactivefilter@propertytest.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "inactivefilter@propertytest.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    create_response = client.post("/api/properties", json={
        "property_name": "Old Residency",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    assert create_response.status_code == 201

    property_id = create_response.get_json()["property"]["id"]

    # Deactivate the property.
    delete_response = client.delete(
        f"/api/properties/{property_id}"
    )

    assert delete_response.status_code == 200

    # Request only inactive properties.
    response = client.get("/api/properties?status=inactive")

    assert response.status_code == 200

    result = response.get_json()

    assert result["count"] == 1
    assert result["properties"][0]["property_name"] == "Old Residency"
    assert result["properties"][0]["is_active"] is False
    
def test_landlord_can_view_all_properties(client):
    # Register and log in a landlord.
    client.post("/auth/register", json={
        "full_name": "All Properties Landlord",
        "email": "allproperties@propertytest.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "allproperties@propertytest.com",
        "password": "PrimeStay123!"
    })

    # Create two properties.
    first_response = client.post("/api/properties", json={
        "property_name": "Active Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    second_response = client.post("/api/properties", json={
        "property_name": "Inactive House",
        "property_type": "house",
        "address_line": "Vijay Nagar",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452010"
    })

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    # Deactivate the second property.
    inactive_id = second_response.get_json()["property"]["id"]

    delete_response = client.delete(
        f"/api/properties/{inactive_id}"
    )

    assert delete_response.status_code == 200

    # Request all properties.
    response = client.get("/api/properties?status=all")

    assert response.status_code == 200

    result = response.get_json()

    assert result["count"] == 2

    active_properties = [
        item for item in result["properties"]
        if item["is_active"] is True
    ]

    inactive_properties = [
        item for item in result["properties"]
        if item["is_active"] is False
    ]

    assert len(active_properties) == 1
    assert len(inactive_properties) == 1
    
def test_invalid_property_status_filter_is_rejected(client):
    # Register and log in a landlord.
    client.post("/auth/register", json={
        "full_name": "Invalid Filter Landlord",
        "email": "invalidfilter@propertytest.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "invalidfilter@propertytest.com",
        "password": "PrimeStay123!"
    })

    # Request an unsupported property status.
    response = client.get("/api/properties?status=deleted")

    assert response.status_code == 400

    result = response.get_json()

    assert result["error"] == (
        "Invalid status. Use active, inactive, or all."
    )