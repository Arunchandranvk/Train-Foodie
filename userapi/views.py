from django.shortcuts import render
from admin1.models import Customer,Food,Review,Order,Cart,CartItem,Category,Vendor
from userapi.serializers import CustomerSerializer,CategorySerializer,VendorSerializer,FoodSerializer,CartSerializer,CartItemsSerializer,ReviewSerializer,OrderSerializer,RestaurantReviewSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet,ViewSet
from rest_framework.decorators import action
from rest_framework import authentication
from rest_framework import permissions
from rest_framework import serializers
from django.utils import timezone
import razorpay
from rest_framework import status
from django.contrib.auth import logout



# Create your views here.

class CustomerCreationView(APIView):
    def post(self,request,*args,**kwargs):
        serializer=CustomerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_type="customer")
            return Response(data={'status':1,'data':serializer.data})
        else:
            return Response(data={'status':0,'data':serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
class CategoryView(ViewSet):
    authentication_classes=[authentication.TokenAuthentication]
    permission_classes=[permissions.IsAuthenticated]
    serializer_class = CategorySerializer
        
    def list(self,request,*args,**kwargs):
        qs=Category.objects.filter(is_active=True)
        serializer=CategorySerializer(qs,many=True)
        return Response(data={'status':1,'data':serializer.data})
    
class VendorView(ViewSet):
    authentication_classes=[authentication.TokenAuthentication]
    permission_classes=[permissions.IsAuthenticated]
    serializer_class = VendorSerializer
        
    def list(self,request,*args,**kwargs):
        qs=Vendor.objects.all()
        serializer=VendorSerializer(qs,many=True)
        return Response(data={'status':1,'data':serializer.data})
    
    def retrieve(self,request,*args,**kwargs):
        id=kwargs.get("pk")
        qs=Vendor.objects.get(id=id)
        serializer=VendorSerializer(qs)
        return Response(data={'status':1,'data':serializer.data})
    
    @action(methods=["post"],detail=True)
    def add_restaurantreview(self,request,*args,**kwargs):
        id=kwargs.get("pk")
        vendor_object=Vendor.objects.get(id=id) 
        user=request.user.customer
        serializer=RestaurantReviewSerializer(data={'status':1,'data':request.data})
        

        if serializer.is_valid():
            serializer.save(user=user,vendor=vendor_object)
            return Response(data={'status':1,'data':serializer.data})
        return Response(data={'status':0,'data':serializer.errors})
    
class FoodView(ViewSet):
    authentication_classes=[authentication.TokenAuthentication]
    permission_classes=[permissions.IsAuthenticated]
    serializer_class = FoodSerializer
        
    def list(self,request,*args,**kwargs):  
        qs=Food.objects.filter(is_active=True)
        serializer=FoodSerializer(qs,many=True)
        return Response(data={'status':1,'data':serializer.data})
    
    @action(methods=["post"],detail=True)
    def add_to_cart(self, request, *args, **kwargs):
        food_id = kwargs.get("pk")
        food_object = Food.objects.get(id=food_id)
        cart_object = request.user.customer.cart

        existing_cart_item=cart_object.cartitem.filter(food=food_object).first()
        
        if existing_cart_item:
            new_quantity=int(request.data.get('quantity',1))
            existing_cart_item.quantity+=new_quantity
            existing_cart_item.save()
            serializer=CartItemsSerializer(existing_cart_item)
            return Response(data={'status':1,'data':serializer.data}, status=status.HTTP_200_OK)
        else:
            serializer=CartItemsSerializer(data=request.data)
            
            if serializer.is_valid():
                serializer.save(cart=cart_object,food=food_object,is_active=True)
                return Response(data={'status':1,'data':serializer.data}, status=status.HTTP_201_CREATED)
            
            return Response(data={'status':0,'data':serializer}.errors, status=status.HTTP_400_BAD_REQUEST)
        

    
    @action(methods=["post"],detail=True)
    def add_review(self,request,*args,**kwargs):
        id=kwargs.get("pk")
        food_object=Food.objects.get(id=id) 
        user=request.user.customer
        serializer=ReviewSerializer(data={'status':1,'data':request.data})
        

        if serializer.is_valid():
            serializer.save(user=user,food=food_object)
            return Response(data={'status':1,'data':serializer.data})
        return Response(data={'status':0,'data':serializer.errors})
    
     
razorpay_client = razorpay.Client(auth=("rzp_test_dGbzyUivWJNxDV", "4iYJQWiT6WT7xYcl1JdHSD3a"))

class CartView(ViewSet):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartSerializer

    def list(self, request, *args, **kwargs):
        user = request.user.customer
        qs = Cart.objects.filter(user=user)
        serializer = CartSerializer(qs, many=True)
        return Response(data={'status':1,'data':serializer.data})
    

    @action(methods=["post"], detail=True)
    def place_order(self, request, *args, **kwargs):
        cart_object = request.user.customer.cart
        user = request.user.customer
        amount = cart_object.calculate_total_amount
        serializer = OrderSerializer(data=request.data)

        if serializer.is_valid():
            order = serializer.save(user=user, cart=cart_object, order_amount=amount)

            try:
                order_amount = int(order.order_amount)
                order_data = {
                    'amount': order_amount,
                    'currency': 'INR',
                    'receipt': f'order_receipt_{order.id}',
                    'payment_capture': 1
                }

                order_response = razorpay_client.order.create(order_data)
                razorpay_order_id = order_response['id']

                order.razorpay_order_id = razorpay_order_id
                order.save()

                user_info={'name':user.name,'phone':user.phone}

                return Response({
                    'status':1,
                    'razorpay_order_id': razorpay_order_id,
                    'order_id': order.id,
                    'amount': order_amount,
                    'user': user_info,
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(e)
                return Response({'error':'Error processing payment'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(data={'status':0,'data':serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    

def sign_out(request):
    logout(request)
    return render("signin")
